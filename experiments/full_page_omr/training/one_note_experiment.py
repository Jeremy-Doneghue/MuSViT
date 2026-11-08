"""Bounded pitch-only pilot, full training mastery and held-out image controls."""

import argparse
from collections import Counter
import json
from pathlib import Path

import torch

from experiments.full_page_omr.datasets.clean_page_data import CleanPageDataset
from experiments.full_page_omr.datasets.one_note_data import CAP, RECIPE
from experiments.full_page_omr.datasets.pilot_data import sha256
from experiments.full_page_omr.diagnostics.clean_page_diagnostics import field_metrics
from experiments.full_page_omr.representation.score_codec import VOCABULARY_SHA256, decode
from experiments.full_page_omr.training.clean_page_experiment import prediction_metrics, recognize, train
from experiments.full_page_omr.training.overfit_pilot import local_encoder, make_model
from experiments.full_page_omr.training.short_staff_experiment import donors, events


def musical_result(target, prediction):
    metrics, source = prediction_metrics(target, prediction)
    reference = [e for bar in events(decode(target)) for e in bar]
    if len(reference) != 1:
        raise ValueError('one-note reference required')
    actual = [e for bar in events(source) for e in bar] if metrics['valid_score'] else None
    single = actual is not None and len(actual) == 1
    return dict(valid=metrics['valid_score'], exact=metrics['exact'], eos=metrics['eos'],
                semantic_exact=bool(metrics['valid_score'] and metrics['structural']['full_semantics_equal']),
                predicted_notes=None if actual is None else len(actual),
                pitch_correct=bool(single and actual[0][0] == reference[0][0]),
                duration_correct=bool(single and actual[0][1] == reference[0][1]),
                joint_correct=bool(single and actual[0] == reference[0]), error=metrics['error'])


def summarize(rows):
    if not rows:
        raise ValueError('empty evaluation')
    metrics = ('valid', 'exact', 'semantic_exact', 'pitch_correct', 'duration_correct', 'joint_correct', 'eos')
    totals = {k: sum(r[k] for r in rows) for k in metrics}
    return dict(count=len(rows), totals=totals,
                rates={k: v / len(rows) for k, v in totals.items()},
                musical_unscorable=sum(not r['valid'] for r in rows),
                errors=dict(Counter(r['error'] for r in rows if r['error'])),
                accuracy_policy='denominator includes every image; invalid or non-single-note outputs cannot earn event credit')


def gate(training, validation, swapped_donor):
    def accurate(summary):
        r = summary['rates']
        return r['valid'] >= .99 and r['joint_correct'] >= .99 and r['exact'] >= .95
    checks = dict(training_mastery=accurate(training), held_out_pitch=accurate(validation),
                  donor_reading=accurate(swapped_donor))
    return dict(checks=checks, passed=all(checks.values()),
                status='single-seed-pass' if all(checks.values()) else 'fail',
                advancement_authorized=False,
                limitation='four held-out absolute pitches with repeated layouts; replicate seed and broaden coverage before curriculum advancement')


@torch.inference_mode()
def evaluate(run):
    run = Path(run)
    config = json.loads((run / 'config.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    manifest_path = Path(config['dataset']) / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['recipe'] != RECIPE or config['max_tokens'] != CAP or result['test_scored']:
        raise ValueError('unexpected pilot contract')
    for path, expected in ((manifest_path, config['dataset_manifest_sha256']),
                           (config['encoder_weights'], config['encoder_weights_sha256']),
                           (config['encoder_config'], config['encoder_config_sha256'])):
        if sha256(path) != expected:
            raise ValueError('run input hash changed')
    output = run / 'one_note_controls'
    output.mkdir(exist_ok=False)
    torch.set_num_threads(4)
    data = {s: CleanPageDataset(config['dataset'], s, config['resolution']) for s in ('train', 'validation')}
    model = make_model(local_encoder(config['encoder_weights'], config['encoder_config']),
                       config['resolution'], CAP, config['width'], config['layers']).to(config['device'])
    model.eval()
    features, targets = {}, {}
    for split, dataset in data.items():
        features[split] = []
        targets[split] = [t.tolist() for _, t in dataset.samples]
        for image, _ in dataset.samples:
            if config['device'] == 'mps':
                torch.mps.empty_cache()
            features[split].append(model.forward_encoder(image.to(config['device'])).permute(0, 2, 1).contiguous())
    indices = donors(data['validation'].records)
    swapped_features = [features['validation'][i] for i in indices]
    report = dict(recipe=RECIPE, seed=config['seed'], family_counts=manifest['family_counts'],
                  dataset_manifest_sha256=config['dataset_manifest_sha256'],
                  implementation_sha256=sha256(__file__), checkpoints={},
                  label='unseen absolute pitch-position diagnostic; not source-composition transfer')
    for checkpoint in ('best', 'last'):
        state = torch.load(run / f'{checkpoint}.pt', map_location='cpu', weights_only=True)
        if state['vocabulary_sha256'] != VOCABULARY_SHA256 or state['step'] != result['selected_step' if checkpoint == 'best' else 'steps']:
            raise ValueError('checkpoint identity mismatch')
        loaded = model.load_state_dict(state['trainable_state'], strict=False)
        if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
            raise ValueError('incompatible checkpoint')
        model.eval()
        # Full training mastery, not the shared trainer's first-three sample.
        recognize(model, features['train'], targets['train'], data['train'].records, output, checkpoint + '_train_all')
        recognize(model, swapped_features, targets['validation'], data['validation'].records, output, checkpoint + '_swapped')
        rows = {}
        for split in ('train', 'validation'):
            folder = output / (checkpoint + '_train_all') if split == 'train' else run / ('validation' if checkpoint == 'best' else 'last_validation')
            rows[split] = []
            for record, target in zip(data[split].records, targets[split]):
                tokens = json.loads((folder / (record['name'] + '.json')).read_text())['tokens']
                rows[split].append(dict(name=record['name'], pitch=record['pitch'],
                                        family_id=record['family_id'], **musical_result(target, tokens)))
        swapped_rows, donor_rows = [], []
        for index, record in enumerate(data['validation'].records):
            prediction = json.loads((output / (checkpoint + '_swapped') / (record['name'] + '.json')).read_text())['tokens']
            donor = indices[index]
            swapped_rows.append(musical_result(targets['validation'][index], prediction))
            donor_rows.append(musical_result(targets['validation'][donor], prediction))
        summaries = {s: summarize(rs) for s, rs in rows.items()}
        swapped_original, swapped_donor = summarize(swapped_rows), summarize(donor_rows)
        by_pitch = {p: summarize([r for r in rows['validation'] if r['pitch'] == p]) for p in manifest['held_out_pitches']}
        report['checkpoints'][checkpoint] = dict(
            step=state['step'], checkpoint_sha256=sha256(run / f'{checkpoint}.pt'),
            matched=summaries, by_held_out_pitch=by_pitch,
            swapped_against_recipient=swapped_original, swapped_against_donor=swapped_donor,
            gold_prefix={label: field_metrics(model, fs, targets['validation'])
                         for label, fs in (('matched', features['validation']), ('swapped', swapped_features))},
            gate=gate(summaries['train'], summaries['validation'], swapped_donor),
            examples=rows,
            swaps=[dict(recipient=r['name'], donor=data['validation'].records[indices[i]]['name'],
                        recipient_metrics=swapped_rows[i], donor_metrics=donor_rows[i])
                   for i, r in enumerate(data['validation'].records)])
    report['trajectory'] = {}
    for step in config.get('snapshot_steps', []):
        if step > result['steps']:
            continue
        path = run / f'step_{step:08d}.pt'
        state = torch.load(path, map_location='cpu', weights_only=True)
        if state['step'] != step or state['vocabulary_sha256'] != VOCABULARY_SHA256:
            raise ValueError('snapshot identity mismatch')
        if step == result['steps']:
            # Already decoded every training and validation image at last.pt.
            if any(not torch.equal(value, state['trainable_state'][key])
                   for key, value in torch.load(run / 'last.pt', map_location='cpu', weights_only=True)['trainable_state'].items()):
                raise ValueError('final snapshot differs from last checkpoint')
            report['trajectory'][str(step)] = dict(step=step, checkpoint_sha256=sha256(path),
                matched=report['checkpoints']['last']['matched'],
                by_held_out_pitch=report['checkpoints']['last']['by_held_out_pitch'],
                predictions='reuse last checkpoint outputs')
            continue
        loaded = model.load_state_dict(state['trainable_state'], strict=False)
        if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
            raise ValueError('incompatible snapshot')
        model.eval()
        rows = {}
        for split in ('train', 'validation'):
            label = f'step_{step:08d}_{split}'
            recognize(model, features[split], targets[split], data[split].records, output, label)
            rows[split] = []
            for record, target in zip(data[split].records, targets[split]):
                pred = json.loads((output / label / (record['name'] + '.json')).read_text())['tokens']
                rows[split].append(dict(name=record['name'], pitch=record['pitch'],
                    family_id=record['family_id'], **musical_result(target, pred)))
        report['trajectory'][str(step)] = dict(step=step, checkpoint_sha256=sha256(path),
            matched={split: summarize(rs) for split, rs in rows.items()}, examples=rows,
            by_held_out_pitch={p: summarize([r for r in rows['validation'] if r['pitch'] == p])
                               for p in manifest['held_out_pitches']})
    report['unreached_snapshot_steps'] = [s for s in config.get('snapshot_steps', []) if s > result['steps']]
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    return report


def training_args(args):
    manifest = json.loads((Path(args.dataset) / 'manifest.json').read_text())
    if manifest['recipe'] != RECIPE or manifest['max_tokens'] != CAP:
        raise ValueError('expected fixed one-note pitch dataset')
    extended = getattr(args, 'extended', False)
    max_steps, max_seconds = (40000, 900) if extended else (8000, 300)
    if not (1 <= args.steps <= max_steps and 1 <= args.max_train_seconds <= max_seconds):
        raise ValueError(f'pilot limited to {max_steps} updates and {max_seconds} training-loop seconds')
    if not (1 <= args.eval_every <= args.steps):
        raise ValueError('evaluation interval must fit update bound')
    args.resolution = 1024
    args.max_tokens = CAP
    args.width, args.layers, args.lr = 128, 2, .001
    args.skip_test, args.evaluate_last = True, True
    if extended:
        args.snapshot_steps = [s for s in (8000, 16000, 24000, 40000) if s <= args.steps]
    args.pilot_implementation_sha256 = sha256(__file__)
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('train')
    for name in ('dataset', 'output', 'encoder-weights', 'encoder-config'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--device', choices=('cpu', 'mps', 'cuda'), default='mps')
    p.add_argument('--seed', type=int, choices=(7, 19), default=7)
    p.add_argument('--extended', action='store_true', help='Permit the fixed 40000-update/900-second comparison and save trajectory snapshots')
    p.add_argument('--steps', type=int, default=8000)
    p.add_argument('--max-train-seconds', type=int, default=300)
    p.add_argument('--eval-every', type=int, default=400)
    p = sub.add_parser('evaluate')
    p.add_argument('--run', required=True)
    args = parser.parse_args()
    if args.command == 'evaluate':
        report = evaluate(args.run)
        print(json.dumps({k: v['gate'] for k, v in report['checkpoints'].items()}, indent=2))
        return
    del args.command
    train(training_args(args))
    report = evaluate(args.output)
    print(json.dumps({k: v['gate'] for k, v in report['checkpoints'].items()}, indent=2))


if __name__ == '__main__':
    main()
