"""Evaluation-only transfer probes for the memorized single-note contrast."""
import argparse
import json
from pathlib import Path

import torch

from experiments.full_page_omr.training.overfit_pilot import evaluate, local_encoder, make_model
from experiments.full_page_omr.datasets.pilot_data import PilotDataset, sha256
from experiments.full_page_omr.representation.score_codec import VOCABULARY_SHA256


def probe(run, dataset, output, encoder_config):
    run, output = Path(run),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    config = json.loads((run/'config.json').read_text())
    if sha256(config['encoder_weights']) != config['encoder_weights_sha256']:
        raise ValueError('encoder weights changed')
    if json.loads(Path(encoder_config).read_text()) != config['encoder_config']:
        raise ValueError('encoder configuration changed')
    torch.set_num_threads(4)
    model = make_model(local_encoder(config['encoder_weights'],encoder_config),config['resolution'],
                       config['maxlen'],config['width'],config['layers']).to(config['device'])
    checkpoint = torch.load(run/'last.pt',map_location='cpu',weights_only=True)
    if checkpoint['vocabulary_sha256'] != VOCABULARY_SHA256:
        raise ValueError('vocabulary mismatch')
    loaded = model.load_state_dict(checkpoint['trainable_state'],strict=False)
    if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
        raise ValueError('incompatible checkpoint')
    data = PilotDataset(dataset,config['resolution'])
    targets = [tokens.tolist() for _,tokens in data.samples]
    if max(map(len,targets)) > config['maxlen']:
        raise ValueError('target exceeds model cap')
    model.eval()
    with torch.no_grad():
        features = [model.forward_encoder(image.to(config['device'])).permute(0,2,1).contiguous()
                    for image,_ in data.samples]
    result = evaluate(model,features,targets,data.records,output,checkpoint['step'])
    known = {r['name']:target for r,target in zip(data.records,targets) if r['name'] in config['selected_names']}
    if set(known) != set(config['selected_names']):
        raise ValueError('evaluation dataset must contain the memorized controls')
    comparisons = []
    for record in data.records:
        tokens = json.loads((output/f"eval_{checkpoint['step']:05d}"/f"{record['name']}.json").read_text())['tokens']
        comparisons.append(dict(name=record['name'],was_trained=record['name'] in known,
                                matches_memorized=[name for name,target in known.items() if tokens==target]))
    report = dict(final=result,known_output_matches=comparisons,training_updates=0,
                  checkpoint_sha256=sha256(run/'last.pt'),dataset_manifest_sha256=sha256(Path(dataset)/'manifest.json'),
                  encoder_weights_sha256=config['encoder_weights_sha256'],implementation_sha256=sha256(__file__),
                  limitation='Post-hoc untrained variants of a training composition; not source-disjoint generalization.')
    (output/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(comparisons,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--encoder-config',required=True)
    probe(**vars(parser.parse_args()))
