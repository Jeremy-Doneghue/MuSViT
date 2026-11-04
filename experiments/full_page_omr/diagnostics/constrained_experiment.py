"""Compare constrained decoding against saved unconstrained validation predictions.

Evaluation only. Never trains, loads test pages, selects a checkpoint, repairs
outputs, or supplies reference length/content to the constrained decoder.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from experiments.full_page_omr.paths import PACKAGE_ROOT
import time

import torch

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset
from experiments.full_page_omr.training.clean_page_experiment import prediction_metrics
from experiments.full_page_omr.representation.constrained_decoding import constrained_greedy
from experiments.full_page_omr.training.overfit_pilot import local_encoder, make_model
from experiments.full_page_omr.datasets.pilot_data import sha256
from experiments.full_page_omr.representation.score_codec import VOCABULARY_SHA256


def aggregate(examples):
    return dict(count=len(examples), exact=sum(e['exact'] for e in examples),
                valid=sum(e['valid_score'] for e in examples), eos=sum(e['eos'] for e in examples),
                token_error=sum(e['token_edits'] for e in examples)/sum(e['reference_tokens'] for e in examples),
                structural_scored=sum(e['valid_score'] for e in examples),
                examples=examples)


def evaluate(run, output, checkpoints=('best', 'last'), device='mps'):
    run, output = Path(run), Path(output)
    config = json.loads((run/'config.json').read_text())
    result = json.loads((run/'result.json').read_text())
    for path, expected in ((config['encoder_weights'],config['encoder_weights_sha256']),
                           (config['encoder_config'],config['encoder_config_sha256']),
                           (Path(config['dataset'])/'manifest.json',config['dataset_manifest_sha256'])):
        if sha256(path) != expected:
            raise ValueError(f'input hash changed: {path}')
    if config['vocabulary_sha256'] != VOCABULARY_SHA256:
        raise ValueError('vocabulary changed')
    if device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('MPS unavailable; no silent CPU fallback')
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    data = CleanPageDataset(config['dataset'], 'validation', config['resolution'])
    # Targets below are used only for scoring, after prediction.
    model = make_model(local_encoder(config['encoder_weights'],config['encoder_config']),
                       config['resolution'],config['max_tokens'],config['width'],config['layers']).to(device)
    model.eval()
    features = []
    with torch.inference_mode():
        for image, _ in data.samples:
            if device == 'mps':
                torch.mps.empty_cache()
            features.append(model.forward_encoder(image.to(device)).permute(0,2,1).contiguous())
    source_paths = {
        'constrained_experiment.py': 'diagnostics/constrained_experiment.py',
        'constrained_decoding.py': 'representation/constrained_decoding.py',
        'score_codec.py': 'representation/score_codec.py',
        'score_semantics.py': 'representation/score_semantics.py',
        'overfit_pilot.py': 'training/overfit_pilot.py',
    }
    report = dict(run=str(run), device=device, started_utc=datetime.now(timezone.utc).isoformat(),
                  baseline_config_sha256=sha256(run/'config.json'),
                  baseline_result_sha256=sha256(run/'result.json'),
                  vocabulary_sha256=VOCABULARY_SHA256,
                  implementation_sha256={name:sha256(PACKAGE_ROOT / source_paths[name]) for name in
                    ('constrained_experiment.py','constrained_decoding.py','score_codec.py','score_semantics.py','overfit_pilot.py')},
                  max_tokens=config['max_tokens'], test_scored=False, training=False,
                  checkpoints={},
                  limitation='Grammar completion is not full codec/semantic validity or visual fidelity. Six development pages, no checkpoint selection.')
    (output/'config.json').write_text(json.dumps(report,indent=2))
    for checkpoint_name in checkpoints:
        checkpoint_path = run/f'{checkpoint_name}.pt'
        checkpoint = torch.load(checkpoint_path,map_location='cpu',weights_only=True)
        expected_step = result['selected_step'] if checkpoint_name == 'best' else result['steps']
        if checkpoint['step'] != expected_step or checkpoint['vocabulary_sha256'] != VOCABULARY_SHA256:
            raise ValueError('checkpoint identity changed')
        loaded = model.load_state_dict(checkpoint['trainable_state'],strict=False)
        if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
            raise ValueError('incompatible checkpoint')
        baseline_dir = run/('validation' if checkpoint_name == 'best' else 'last_validation')
        folder = output/checkpoint_name
        folder.mkdir(exist_ok=False)
        baseline, constrained = [], []
        for feature, record, (_, target) in zip(features, data.records, data.samples):
            saved_path = baseline_dir/f"{record['name']}.json"
            saved = json.loads(saved_path.read_text())
            before, _ = prediction_metrics(target.tolist(), saved['tokens'])
            if any(saved['metrics'][k] != v for k,v in before.items()):
                raise ValueError('saved baseline metrics disagree')
            baseline.append(dict(before,name=record['name'],prediction_sha256=sha256(saved_path)))
            started = time.perf_counter()
            prediction = constrained_greedy(model,feature,config['max_tokens'])
            seconds = time.perf_counter()-started
            metrics, xml = prediction_metrics(target.tolist(),prediction.tokens)
            item = dict(metrics,name=record['name'],kind=record['kind'],
                        grammar_complete=prediction.grammar_complete,interventions=prediction.interventions,
                        stop_reason=prediction.stop_reason,seconds=seconds)
            constrained.append(item)
            (folder/f"{record['name']}.json").write_text(json.dumps(dict(tokens=prediction.tokens,metrics=item),indent=2))
            # prediction_metrics can return XML whose semantic validation failed.
            if metrics['valid_score']:
                (folder/f"{record['name']}.musicxml").write_text(xml)
            print(json.dumps(dict(checkpoint=checkpoint_name,**{k:item[k] for k in
                ('name','grammar_complete','valid_score','error','interventions','seconds')})),flush=True)
        comparison = dict(step=expected_step,checkpoint_sha256=sha256(checkpoint_path),
                          baseline=aggregate(baseline),constrained=aggregate(constrained),
                          grammar_complete=sum(e['grammar_complete'] for e in constrained),
                          interventions=sum(e['interventions'] for e in constrained))
        report['checkpoints'][checkpoint_name] = comparison
        (folder/'summary.json').write_text(json.dumps(comparison,indent=2))
        (output/'result.json').write_text(json.dumps(report,indent=2))
    report['completed'] = True
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--checkpoints',nargs='+',choices=('best','last'),default=['best','last'])
    parser.add_argument('--device',choices=('mps','cpu','cuda'),default='mps')
    args=parser.parse_args()
    evaluate(args.run,args.output,args.checkpoints,args.device)
