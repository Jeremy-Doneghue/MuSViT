"""Post-run gold-prefix field errors and same-instrument image swaps.

This does not train, select checkpoints, score test pages, or measure autonomous
musical accuracy. Roles are assigned from the valid reference prefix.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import torch
import torch.nn.functional as F

from .clean_page_data import CleanPageDataset
from .overfit_pilot import local_encoder, make_model, swap_indices
from .pilot_data import sha256
from .score_codec import VOCABULARY, VOCABULARY_SHA256


def token_roles(tokens):
    stack, attribute, roles = [], None, []
    for token in tokens:
        word = VOCABULARY[token]
        if word.startswith('E:'):
            roles.append('element')
            stack.append(word[2:])
        elif word.startswith('A:'):
            attribute = word[2:]
            roles.append('attribute_name')
        elif word.startswith(('V:', 'B:')):
            roles.append(('attribute_value:' + stack[-1] + '@' + attribute)
                         if attribute else ('text_value:' + stack[-1]))
        else:
            roles.append('control:' + word)
            if word == '<value-end>':
                attribute = None
            elif word == '<end>':
                stack.pop()
    return roles


@torch.inference_mode()
def field_metrics(model, features, targets):
    totals = defaultdict(lambda: dict(tokens=0, errors=0, loss_sum=0.))
    for feature, target in zip(features, targets):
        if feature.device.type == 'mps':
            torch.mps.empty_cache()
        sequence = torch.tensor([target], device=feature.device)
        logits = model.forward_decoder(feature, sequence[:, :-1]).logits
        losses = F.cross_entropy(logits, sequence[:, 1:], reduction='none')[0].tolist()
        predicted = logits.argmax(dim=1)[0].tolist()
        for role, loss, actual, expected in zip(token_roles(target)[1:], losses, predicted, target[1:]):
            totals[role]['tokens'] += 1
            totals[role]['errors'] += actual != expected
            totals[role]['loss_sum'] += loss
        del logits
    count = sum(v['tokens'] for v in totals.values())
    errors = sum(v['errors'] for v in totals.values())
    loss = sum(v['loss_sum'] for v in totals.values())
    return dict(tokens=count, errors=errors, cross_entropy=loss/count,
                next_token_accuracy=1-errors/count,
                roles={k:dict(v, accuracy=1-v['errors']/v['tokens'],
                              cross_entropy=v['loss_sum']/v['tokens']) for k,v in sorted(totals.items())})


def diagnose(run, checkpoint_name, device=None):
    run = Path(run)
    output = run/f'field_diagnostics_{checkpoint_name}.json'
    if output.exists():
        raise FileExistsError(output)
    config = json.loads((run/'config.json').read_text())
    device = device or config['device']
    result = json.loads((run/'result.json').read_text())
    for path, expected in ((config['encoder_weights'],config['encoder_weights_sha256']),
                           (config['encoder_config'],config['encoder_config_sha256']),
                           (Path(config['dataset'])/'manifest.json',config['dataset_manifest_sha256'])):
        if sha256(path) != expected:
            raise ValueError('run input hash changed')
    torch.set_num_threads(4)
    model = make_model(local_encoder(config['encoder_weights'],config['encoder_config']),
                       config['resolution'],config['max_tokens'],config['width'],config['layers']).to(device)
    checkpoint_path = run/f'{checkpoint_name}.pt'
    checkpoint = torch.load(checkpoint_path,map_location='cpu',weights_only=True)
    expected_step = result['selected_step'] if checkpoint_name == 'best' else result['steps']
    if checkpoint['step'] != expected_step or checkpoint['vocabulary_sha256'] != VOCABULARY_SHA256:
        raise ValueError('checkpoint identity changed')
    loaded = model.load_state_dict(checkpoint['trainable_state'],strict=False)
    if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
        raise ValueError('incompatible checkpoint')
    model.eval()
    reports = {}
    for split in ('train','validation'):
        data = CleanPageDataset(config['dataset'],split,config['resolution'])
        records, samples = data.records[:6], data.samples[:6]
        donors = swap_indices(records,within_kind=True)
        with torch.no_grad():
            features = [model.forward_encoder(image.to(device)).permute(0,2,1).contiguous()
                        for image,_ in samples]
        targets = [tokens.tolist() for _,tokens in samples]
        matched = field_metrics(model,features,targets)
        swapped = field_metrics(model,[features[i] for i in donors],targets)
        reports[split] = dict(matched=matched,swapped=swapped,
                              swapped_minus_matched_ce=swapped['cross_entropy']-matched['cross_entropy'],
                              pairs=[dict(target=r['name'],donor=records[donors[i]]['name']) for i,r in enumerate(records)])
    report = dict(checkpoint=checkpoint_name,step=expected_step,device=device,checkpoint_sha256=sha256(checkpoint_path),
                  implementation_sha256=sha256(__file__),splits=reports,
                  limitation='Gold-prefix field/token diagnostics only; not autonomous music accuracy. Test untouched.')
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(checkpoint=checkpoint_name,step=expected_step,
                         splits={s:{k:v for k,v in r.items() if k not in ('matched','swapped','pairs')}
                                 for s,r in reports.items()}),indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--checkpoint',choices=('best','last'),default='best')
    parser.add_argument('--device',choices=('cpu','mps','cuda'),help='Explicit diagnostic device override; no training')
    args = parser.parse_args()
    diagnose(args.run,args.checkpoint,args.device)
