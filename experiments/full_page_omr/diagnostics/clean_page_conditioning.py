"""Post-run image-swap diagnostic on training pages; never selects a checkpoint."""

import argparse
import json
from pathlib import Path

import torch

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset
from experiments.full_page_omr.training.clean_page_experiment import teacher_metrics
from experiments.full_page_omr.training.overfit_pilot import local_encoder, make_model
from experiments.full_page_omr.datasets.pilot_data import sha256


def diagnose(run):
    run = Path(run)
    output = run / 'conditioning_teacher.json'
    if output.exists():
        raise FileExistsError(output)
    config = json.loads((run/'config.json').read_text())
    result = json.loads((run/'result.json').read_text())
    if sha256(config['encoder_weights']) != config['encoder_weights_sha256']:
        raise ValueError('encoder weights changed')
    data = CleanPageDataset(config['dataset'], 'train', config['resolution'])
    # Two pages per kind, selected in advance by generation order. Swap only
    # within instrument so the control cannot be solved from instrument identity.
    samples, records = data.samples[:6], data.records[:6]
    if len(samples) != 6 or any(records[i]['kind'] != records[(i+3)%6]['kind'] for i in range(6)):
        raise ValueError('diagnostic requires two training pages per instrument')
    torch.set_num_threads(4)
    model = make_model(local_encoder(config['encoder_weights'],config['encoder_config']),
                       config['resolution'],config['max_tokens'],config['width'],config['layers']).to(config['device'])
    checkpoint = torch.load(run/'best.pt',map_location='cpu',weights_only=True)
    if checkpoint['step'] != result['selected_step']:
        raise ValueError('selected checkpoint changed')
    loaded = model.load_state_dict(checkpoint['trainable_state'],strict=False)
    if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
        raise ValueError('incompatible checkpoint')
    model.eval()
    with torch.no_grad():
        features = [model.forward_encoder(image.to(config['device'])).permute(0,2,1).contiguous()
                    for image,_ in samples]
    targets = [tokens.tolist() for _,tokens in samples]
    matched = teacher_metrics(model,features,targets)
    swapped = teacher_metrics(model,features[3:]+features[:3],targets)
    report = dict(selected_step=result['selected_step'],split='train',count=6,
                  matched=matched,swapped_within_instrument=swapped,
                  swapped_minus_matched_cross_entropy=swapped['cross_entropy']-matched['cross_entropy'],
                  checkpoint_sha256=sha256(run/'best.pt'),
                  pairs=[dict(target=r['name'],donor_image=records[(i+3)%6]['name']) for i,r in enumerate(records)],
                  limitation='Gold-prefix training-page diagnostic only; not autonomous or held-out recognition.')
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    diagnose(parser.parse_args().run)
