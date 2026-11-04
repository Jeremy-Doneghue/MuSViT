"""Bounded short-staff training and checkpoint-separated transfer controls."""
import argparse
from collections import Counter
import json
from pathlib import Path

import editdistance
import torch

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset
from experiments.full_page_omr.diagnostics.clean_page_diagnostics import field_metrics
from experiments.full_page_omr.training.clean_page_experiment import prediction_metrics, recognize, train
from experiments.full_page_omr.training.overfit_pilot import local_encoder, make_model
from experiments.full_page_omr.datasets.pilot_data import sha256
from experiments.full_page_omr.representation.score_codec import decode, VOCABULARY_SHA256
from experiments.full_page_omr.representation.score_semantics import inspect_score
from experiments.full_page_omr.datasets.short_staff_data import RECIPE, CAP


def events(source):
    return [[(tuple(e['pitch']) if e['pitch'] else None, e['duration']) for e in b['events']]
            for p in inspect_score(source)['parts'] for b in p['measures']]


def music_metrics(reference, actual):
    """Whole-score validity is checked by caller; never repair invalid outputs.

    Edit distances include insertions/deletions. Positional accuracies are only
    scored for measures with equal event counts, and report their coverage.
    """
    gold, pred = events(reference), events(actual)
    result = dict(reference_notes=sum(map(len, gold)), predicted_notes=sum(map(len, pred)),
                  pitch_edits=0, duration_edits=0, event_edits=0, aligned_notes=0,
                  pitch_correct=0, duration_correct=0, joint_correct=0,
                  missing_notes=0, extra_notes=0,
                  missing_measures=max(0,len(gold)-len(pred)), extra_measures=max(0,len(pred)-len(gold)))
    for i in range(max(len(gold),len(pred))):
        a, b = gold[i] if i<len(gold) else [], pred[i] if i<len(pred) else []
        result['event_edits'] += editdistance.eval(a,b)
        result['pitch_edits'] += editdistance.eval([e[0] for e in a],[e[0] for e in b])
        result['duration_edits'] += editdistance.eval([e[1] for e in a],[e[1] for e in b])
        result['missing_notes'] += max(0,len(a)-len(b))
        result['extra_notes'] += max(0,len(b)-len(a))
        if len(a)==len(b):
            result['aligned_notes'] += len(a)
            for x,y in zip(a,b):
                result['pitch_correct'] += x[0]==y[0]
                result['duration_correct'] += x[1]==y[1]
                result['joint_correct'] += x==y
    return result


def donors(records):
    """Rotate across families while matching variant, never swap with an edit sibling."""
    answer=[]
    for i,r in enumerate(records):
        j=next((i+k)%len(records) for k in range(1,len(records))
               if records[(i+k)%len(records)]['family_id'] != r['family_id']
               and records[(i+k)%len(records)]['variant']==r['variant'])
        answer.append(j)
    return answer


def prior_baseline(training, validation):
    counts = [Counter(),Counter()]
    for source in training:
        for bar in events(source):
            for event in bar:
                for i,value in enumerate(event): counts[i][value]+=1
    modes = [c.most_common(1)[0][0] for c in counts]
    refs = [e for source in validation for bar in events(source) for e in bar]
    return dict(label='training marginal mode; reference event slots supplied, not autonomous transcription',
                pitch_mode=modes[0],duration_mode=modes[1],notes=len(refs),
                pitch_accuracy=sum(e[0]==modes[0] for e in refs)/len(refs),
                duration_accuracy=sum(e[1]==modes[1] for e in refs)/len(refs))


@torch.inference_mode()
def evaluate(run):
    run=Path(run)
    config=json.loads((run/'config.json').read_text())
    result=json.loads((run/'result.json').read_text())
    for path,expected in ((config['encoder_weights'],config['encoder_weights_sha256']),
                          (config['encoder_config'],config['encoder_config_sha256']),
                          (Path(config['dataset'])/'manifest.json',config['dataset_manifest_sha256'])):
        if sha256(path)!=expected: raise ValueError('input hash changed')
    output=run/'transfer_controls'
    output.mkdir(exist_ok=False)
    data={s:CleanPageDataset(config['dataset'],s,config['resolution']) for s in ('train','validation')}
    validation=data['validation']
    records=validation.records
    targets=[t.tolist() for _,t in validation.samples]
    sources={s:[(Path(config['dataset'])/r['source']).read_text() for r in d.records] for s,d in data.items()}
    report=dict(prior=prior_baseline(sources['train'],sources['validation']),checkpoints={},
                dataset_manifest_sha256=config['dataset_manifest_sha256'],implementation_sha256=sha256(__file__))
    model=make_model(local_encoder(config['encoder_weights'],config['encoder_config']),config['resolution'],
                     config['max_tokens'],config['width'],config['layers']).to(config['device'])
    model.eval()
    features=[]
    for image,_ in validation.samples:
        if config['device']=='mps': torch.mps.empty_cache()
        features.append(model.forward_encoder(image.to(config['device'])).permute(0,2,1).contiguous())
    donor_indices=donors(records)
    swapped=[features[i] for i in donor_indices]
    for checkpoint,folder in (('best','validation'),('last','last_validation')):
        state=torch.load(run/f'{checkpoint}.pt',map_location='cpu',weights_only=True)
        if state['vocabulary_sha256']!=VOCABULARY_SHA256 or state['step']!=(result['selected_step'] if checkpoint=='best' else result['steps']):
            raise ValueError('checkpoint identity mismatch')
        loaded=model.load_state_dict(state['trainable_state'],strict=False)
        if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
            raise ValueError('incompatible checkpoint')
        fields={label:field_metrics(model,fs,targets) for label,fs in (('matched',features),('swapped',swapped))}
        swap_result=recognize(model,swapped,targets,records,output,checkpoint+'_swapped')
        rows=[]
        for i,r in enumerate(records):
            saved=json.loads((run/folder/(r['name']+'.json')).read_text())
            pred=saved['tokens']
            metrics,source=prediction_metrics(targets[i],pred)
            swap_tokens=json.loads((output/(checkpoint+'_swapped')/(r['name']+'.json')).read_text())['tokens']
            rows.append(dict(name=r['name'],family_id=r['family_id'],variant=r['variant'],
                             valid=metrics['valid_score'],exact=metrics['exact'],
                             music=music_metrics(decode(targets[i]),source) if metrics['valid_score'] else None,
                             swap_donor=records[donor_indices[i]]['name'],
                             swap_matches_donor=swap_tokens==targets[donor_indices[i]]))
        musical_summary={}
        for variant in ('base','pitch','rhythm'):
            subset=[r for r in rows if r['variant']==variant]
            valid=[r['music'] for r in subset if r['music'] is not None]
            totals={k:sum(r[k] for r in valid) for k in valid[0]} if valid else None
            musical_summary[variant]=dict(count=len(subset),valid=len(valid),
                exact=sum(r['exact'] for r in subset),valid_only_totals=totals)
        field_deltas={role:dict(
            cross_entropy=fields['swapped']['roles'][role]['cross_entropy']-value['cross_entropy'],
            accuracy=fields['swapped']['roles'][role]['accuracy']-value['accuracy'])
            for role,value in fields['matched']['roles'].items()}
        families={r['family_id'] for r in rows}
        report['checkpoints'][checkpoint]=dict(step=state['step'],checkpoint_sha256=sha256(run/f'{checkpoint}.pt'),
            gold_prefix=fields,swapped_minus_matched_by_field=field_deltas,
            musical_summary=musical_summary,swapped=swap_result,examples=rows,
            exact_families_all_three=sum(all(r['exact'] for r in rows if r['family_id']==f) for f in families),
            validity=sum(r['valid'] for r in rows), families=len(families),
            musical_unscorable=sum(not r['valid'] for r in rows))
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('train')
    for name in ('dataset','output','encoder-weights','encoder-config'): p.add_argument('--'+name,required=True)
    p.add_argument('--device',choices=('cpu','mps','cuda'),default='mps')
    p.add_argument('--steps',type=int,default=9600)
    p.add_argument('--max-train-seconds',type=int,default=1800)
    p.add_argument('--eval-every',type=int,default=400)
    p=sub.add_parser('evaluate'); p.add_argument('--run',required=True)
    args=parser.parse_args()
    if args.command=='evaluate': evaluate(args.run); return
    del args.command
    manifest=json.loads((Path(args.dataset)/'manifest.json').read_text())
    if manifest['recipe']!=RECIPE: raise ValueError('expected short-staff dataset')
    args.resolution=1024; args.max_tokens=CAP; args.width=128; args.layers=2
    args.lr=.001; args.seed=7; args.skip_test=True; args.evaluate_last=True
    train(args)
    evaluate(args.output)


if __name__=='__main__': main()
