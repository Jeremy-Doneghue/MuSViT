"""Fixed-update comparison of four versus sixteen training placements per pitch."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import torch

from experiments.full_page_omr.datasets.pitch_target_data import load, image_tensor, LAYOUTS, PLACEMENT_RECIPE
from experiments.full_page_omr.datasets.one_note_data import CAP
from experiments.full_page_omr.datasets.pilot_data import sha256
from experiments.full_page_omr.training.overfit_pilot import local_encoder, make_model
from experiments.full_page_omr.training.pitch_target_experiment import train_arm, trainable_state


def control_indices(samples):
    return [i for i,s in enumerate(samples) if tuple(s['record']['translation_pixels']) in LAYOUTS['train']]


def run(args):
    if not 1 <= args.steps <= 16800 or not 1 <= args.max_train_seconds <= 600:
        raise ValueError('bounded to 16800 updates and 600 active seconds per version')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    if args.device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('MPS requires GPU access')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    manifest,samples = load(args.dataset)
    if manifest['recipe'] != PLACEMENT_RECIPE:
        raise ValueError('requires fixed placement recipe')
    encoder = local_encoder(args.encoder_weights,args.encoder_config)
    torch.manual_seed(args.seed)
    model = make_model(encoder,1024,CAP,256,4).to(args.device)
    initial = trainable_state(model)
    torch.save(initial,output/'initial.pt')
    config = dict(vars(args), width=256,layers=4,lr=args.lr,steps_per_version=args.steps,
        vocabulary_sha256=manifest['vocabulary_sha256'],
        dataset_manifest_sha256=sha256(Path(args.dataset)/'manifest.json'),
        encoder_weights_sha256=sha256(args.encoder_weights),
        encoder_config_sha256=sha256(args.encoder_config),
        initial_sha256=sha256(output/'initial.pt'),
        trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        optimizer='AdamW, no decay, clip 1, batch 1, no dropout',
        selection='validation pitch, validity, exactness; earliest tie',
        implementation_sha256={str(p):sha256(p) for p in (
            Path(__file__), Path(__file__).with_name('pitch_target_experiment.py'),
            Path(__file__).with_name('overfit_pilot.py'),
            Path('experiments/full_page_omr/datasets/pitch_target_data.py'),
            Path('experiments/full_page_omr/smt_foundation/modeling_smt.py'))},
        limitation='14 pitch identities with correlated placements; no composition transfer',test_scored=False)
    (output/'config.json').write_text(json.dumps(config,indent=2))
    features={k:[] for k in samples}; hashes={}
    started=time.perf_counter()
    model.eval()
    with torch.no_grad():
        for split,ss in samples.items():
            for sample in ss:
                if args.device=='mps': torch.mps.empty_cache()
                feature=model.forward_encoder(image_tensor(args.dataset,sample['record'],1024).to(args.device)).permute(0,2,1).contiguous()
                hashes[sample['record']['name']]=hashlib.sha256(feature.cpu().numpy().tobytes()).hexdigest()
                features[split].append(feature)
    (output/'feature_hashes.json').write_text(json.dumps(hashes,indent=2))
    config['extraction_seconds']=time.perf_counter()-started
    config['feature_hashes_sha256']=sha256(output/'feature_hashes.json')
    (output/'config.json').write_text(json.dumps(config,indent=2))
    reports={}
    for name,indices in (('control',control_indices(samples['train'])),('expanded',list(range(len(samples['train']))))):
        subset=dict(samples,train=[samples['train'][i] for i in indices])
        feature_subset=dict(features,train=[features['train'][i] for i in indices])
        reports[name]=train_arm(model,initial,feature_subset,subset,'score',args,output/name,args.steps)
    result=dict(versions=reports,initial_weights_shared=True,validation_shared=True,
                matched_steps=reports['control']['steps']==reports['expanded']['steps'],test_scored=False)
    (output/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(completed=True,results={k:v['controls']['selected']['validation']['totals'] for k,v in reports.items()})),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','output','encoder-weights','encoder-config'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--device',choices=('cpu','mps'),default='mps')
    parser.add_argument('--seed',type=int,choices=(7,19),default=7)
    args=parser.parse_args()
    args.lr,args.steps,args.max_train_seconds=.0001,16800,600
    args.evaluation_steps=[560,2800,5600,11200,16800]
    run(args)
