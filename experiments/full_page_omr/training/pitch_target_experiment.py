"""Matched autoregressive score-token versus four-token pitch experiment."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import time

import torch
from torch import nn
import torch.nn.functional as F

from experiments.full_page_omr.datasets.one_note_data import CAP, PITCHES, make_note
from experiments.full_page_omr.datasets.pitch_target_data import image_tensor, load, pitch_to_musicxml
from experiments.full_page_omr.datasets.pilot_data import sha256
from experiments.full_page_omr.paths import PACKAGE_ROOT
from experiments.full_page_omr.representation.score_codec import VOCABULARY_SHA256, W2I, decode
from experiments.full_page_omr.representation.score_semantics import inspect_score
from experiments.full_page_omr.training.clean_page_experiment import teacher_metrics
from experiments.full_page_omr.training.overfit_pilot import CachedGreedy, greedy, local_encoder, make_model

ARMS = ('score', 'pitch')
DECODE_CAPS = {'score': CAP, 'pitch': 8}


def measure(pitch, target, prediction, arm):
    if arm not in ARMS:
        raise ValueError('unknown target arm')
    row = dict(valid=False, target_exact=prediction == target,
               eos=bool(prediction and prediction[-1] == W2I['<eos>']),
               pitch_correct=False, duration_correct=False, joint_correct=False,
               music_exact=False, predicted_pitch=None, error=None)
    source = None
    try:
        source = decode(prediction) if arm == 'score' else pitch_to_musicxml(prediction)
        actual, expected = inspect_score(source), inspect_score(make_note(pitch))
        events = [e for p in actual['parts'] for b in p['measures'] for e in b['events']]
        if len(events) == 1:
            written = events[0]['pitch']
            row['predicted_pitch'] = list(written) if written else None
            row['pitch_correct'] = written == (pitch[0], '0', pitch[1])
            row['duration_correct'] = events[0]['duration'] == '1'
        row.update(valid=True, music_exact=actual == expected,
                   joint_correct=row['pitch_correct'] and row['duration_correct'])
    except ValueError as error:
        row['error'], source = str(error), None
    return row, source


def summarize(rows):
    keys = ('valid', 'target_exact', 'eos', 'pitch_correct', 'duration_correct', 'joint_correct', 'music_exact')
    totals = {k: sum(r[k] for r in rows) for k in keys}
    return dict(count=len(rows), totals=totals, rates={k:v / len(rows) for k,v in totals.items()},
                musical_unscorable=sum(not r['valid'] for r in rows),
                errors=dict(Counter(r['error'] for r in rows if r['error'])))


def donor_indices(records):
    return [next((i+k) % len(records) for k in range(1, len(records))
                 if records[(i+k) % len(records)]['pitch'] != r['pitch']
                 and records[(i+k) % len(records)]['translation_pixels'] == r['translation_pixels'])
            for i, r in enumerate(records)]


@torch.inference_mode()
def evaluate_set(model, features, samples, arm, output, donors=None):
    output = Path(output)
    output.mkdir(exist_ok=False)
    model.eval()
    rows, donor_rows = [], []
    started = time.perf_counter()
    for index, sample in enumerate(samples):
        record = sample['record']
        donor = index if donors is None else donors[index]
        prediction = greedy(model, features[donor], DECODE_CAPS[arm])
        metrics, source = measure(record['pitch'], sample[arm], prediction, arm)
        row = dict(name=record['name'], pitch=record['pitch'],
                   feature_source=samples[donor]['record']['name'], metrics=metrics)
        if donors is not None:
            donor_metrics, _ = measure(samples[donor]['record']['pitch'], samples[donor][arm], prediction, arm)
            row['donor_metrics'] = donor_metrics
            donor_rows.append(donor_metrics)
        (output / (record['name'] + '.json')).write_text(json.dumps(dict(row, tokens=prediction), indent=2))
        if source is not None:
            (output / (record['name'] + '.musicxml')).write_text(source)
        rows.append(row)
    summary = summarize([r['metrics'] for r in rows])
    summary.update(seconds=time.perf_counter() - started,
                   by_pitch={p:summarize([r['metrics'] for r in rows if r['pitch'] == p])
                             for p in sorted({r['pitch'] for r in rows})},
                   examples=rows, directory=output.name)
    if donors is not None:
        summary['against_donor'] = summarize(donor_rows)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(dict(evaluation=str(output), count=len(rows),
        valid=summary['totals']['valid'], pitch_correct=summary['totals']['pitch_correct'],
        exact=summary['totals']['target_exact'], seconds=summary['seconds'])), flush=True)
    return summary


def selection_rank(summary):
    return tuple(summary['totals'][k] for k in ('pitch_correct', 'valid', 'target_exact'))


def trainable_state(model):
    return {k:v.detach().cpu().clone() for k,v in model.state_dict().items() if not k.startswith('encoder.')}


def restore(model, state):
    loaded = model.load_state_dict(state, strict=False)
    if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
        raise ValueError('incompatible trainable state')


def checkpoint(model, step, arm, path):
    torch.save(dict(trainable_state=trainable_state(model), step=step, arm=arm,
                    vocabulary_sha256=VOCABULARY_SHA256), path)


def criterion(training, validation, swapped):
    def passes(summary):
        return (summary['rates']['pitch_correct'] >= .99 and summary['rates']['joint_correct'] >= .99
                and summary['rates']['valid'] >= .99
                and summary['rates']['music_exact'] >= .95)
    checks = dict(training=passes(training), appearance=passes(validation),
                  donor=passes(swapped['against_donor']))
    return dict(checks=checks, passed=all(checks.values()), automatically_advance=False,
                limitation='single seed; 14 shared pitch targets with correlated placements, not composition transfer')


def train_arm(model, initial, features, samples, arm, args, output, target_steps):
    output.mkdir()
    restore(model, initial)
    if any(not torch.equal(v, initial[k]) for k,v in trainable_state(model).items()):
        raise ValueError('arm initialization differs')
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    targets = {s:[sample[arm] for sample in ss] for s,ss in samples.items()}
    with torch.no_grad():
        model.eval()
        prefix = targets['train'][0][:-1][:16]
        cache = CachedGreedy(model, features['train'][0])
        for pos, token in enumerate(prefix):
            incremental = cache.step(token, pos)
        full = model.forward_decoder(features['train'][0], torch.tensor([prefix], device=args.device)).logits[0,:,-1]
        torch.testing.assert_close(incremental, full, atol=2e-4, rtol=2e-4)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0)
    n = len(samples['train'])
    milestones = {n*p for p in (10, 50, 100, 200, 300) if n*p <= target_steps}
    if getattr(args, "evaluation_steps", None):
        milestones = {s for s in args.evaluation_steps if s <= target_steps}
    milestones.add(target_steps)
    order, exposures, history = [], [0]*n, []
    order_hash = hashlib.sha256()
    best_rank, best_step = None, None
    started, diagnostics_seconds = time.perf_counter(), 0.
    losses = []
    for step in range(1, target_steps + 1):
        if args.device == 'mps' and (step == 1 or step % 25 == 0):
            torch.mps.empty_cache()
        if not order:
            order = list(range(n))
            rng.shuffle(order)
        index = order.pop()
        order_hash.update(index.to_bytes(4, 'little'))
        model.train()
        model.encoder.eval()
        optimizer.zero_grad(set_to_none=True)
        sequence = torch.tensor([targets['train'][index]], device=args.device)
        logits = model.forward_decoder(features['train'][index], sequence[:,:-1]).logits
        loss = F.cross_entropy(logits, sequence[:,1:])
        if not torch.isfinite(loss):
            raise RuntimeError('nonfinite loss')
        loss.backward()
        nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.)
        optimizer.step()
        value = loss.item()
        losses.append(value)
        exposures[index] += 1
        del logits, loss
        elapsed = time.perf_counter() - started - diagnostics_seconds
        timed_out = elapsed >= args.max_train_seconds
        if step == 1 or step % 100 == 0:
            row = dict(arm=arm, step=step, loss=value, mean_recent_loss=sum(losses[-100:])/len(losses[-100:]), optimization_seconds=elapsed)
            with (output / 'training.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')
            print(json.dumps(row), flush=True)
        if step in milestones or timed_out:
            diagnostic_start = time.perf_counter()
            checkpoint(model, step, arm, output / f'step_{step:08d}.pt')
            validation = evaluate_set(model, features['validation'], samples['validation'], arm,
                                      output / f'validation_{step:08d}')
            teacher = teacher_metrics(model, features['validation'], targets['validation'])
            row = dict(step=step, validation=validation, teacher=teacher, optimization_seconds=elapsed)
            history.append(row)
            with (output / 'validation.jsonl').open('a') as stream:
                stream.write(json.dumps({k:v for k,v in row.items() if k != 'validation'} |
                    {'validation_totals':validation['totals']}) + '\n')
            rank = selection_rank(validation)
            if best_rank is None or rank > best_rank:
                best_rank, best_step = rank, step
                checkpoint(model, step, arm, output / 'best.pt')
            diagnostics_seconds += time.perf_counter() - diagnostic_start
        if timed_out:
            break
    optimization_seconds = time.perf_counter() - started - diagnostics_seconds
    checkpoint(model, step, arm, output / 'last.pt')
    records = [s['record'] for s in samples['validation']]
    donors = donor_indices(records)
    controls = {}
    for label, chosen_step in (('selected', best_step), ('final', step)):
        file = output / ('best.pt' if label == 'selected' else 'last.pt')
        state = torch.load(file, map_location='cpu', weights_only=True)
        if state['arm'] != arm or state['step'] != chosen_step or state['vocabulary_sha256'] != VOCABULARY_SHA256:
            raise ValueError('checkpoint identity mismatch')
        restore(model, state['trainable_state'])
        training = evaluate_set(model, features['train'], samples['train'], arm, output / (label + '_train'))
        validation = next(h['validation'] for h in history if h['step'] == chosen_step)
        swapped = evaluate_set(model, features['validation'], samples['validation'], arm,
                               output / (label + '_swapped'), donors)
        controls[label] = dict(step=chosen_step, checkpoint_sha256=sha256(file), training=training,
            validation=validation, swapped=swapped, gate=criterion(training, validation, swapped))
    result = dict(arm=arm, steps=step, selected_step=best_step, optimization_seconds=optimization_seconds,
        diagnostics_seconds=diagnostics_seconds, time_bound_reached=timed_out,
        initial_state_identical=True, order_sha256=order_hash.hexdigest(),
        presentations=dict(zip([s['record']['name'] for s in samples['train']], exposures)),
        validation_history=history, controls=controls,
        encoder_frozen=all(not p.requires_grad and p.grad is None for p in model.encoder.parameters()))
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    return result


def run(args):
    if not (1 <= args.presentations <= 300 and 1 <= args.max_train_seconds <= 600):
        raise ValueError('comparison limited to 300 presentations/image and 600 optimization seconds per arm')
    baseline_path = getattr(args, 'medium_lr_baseline', None)
    if baseline_path and getattr(args, 'capacity_comparison', False):
        raise ValueError('choose one comparison mode')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    if args.device == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('MPS requires GPU access; no silent fallback')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    manifest, samples = load(args.dataset)
    model = make_model(local_encoder(args.encoder_weights, args.encoder_config), args.resolution,
                       CAP, args.width, args.layers).to(args.device)
    model.freeze_encoder()
    model.eval()
    initial = trainable_state(model)
    torch.save(dict(trainable_state=initial, vocabulary_sha256=VOCABULARY_SHA256), output / 'initial.pt')
    config = dict(vars(args), recipe=manifest['recipe'], steps_per_arm=len(samples['train'])*args.presentations,
        arms=ARMS, model_max_tokens=CAP, decode_caps=DECODE_CAPS, vocabulary_sha256=VOCABULARY_SHA256,
        dataset_manifest_sha256=sha256(Path(args.dataset) / 'manifest.json'),
        encoder_weights_sha256=sha256(args.encoder_weights), encoder_config_sha256=sha256(args.encoder_config),
        initial_state_sha256=sha256(output / 'initial.pt'),
        implementation_sha256={p.name:sha256(p) for p in (Path(__file__),
            PACKAGE_ROOT / 'datasets/pitch_target_data.py', PACKAGE_ROOT / 'training/overfit_pilot.py',
            PACKAGE_ROOT / 'smt_foundation/modeling_smt.py', PACKAGE_ROOT / 'training/clean_page_experiment.py',
            PACKAGE_ROOT / 'representation/score_codec.py', PACKAGE_ROOT / 'representation/score_semantics.py')},
        trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        torch=torch.__version__, selection='max validation pitch correctness, then validity, then target exactness; earliest tie',
        optimizer=f'AdamW lr {args.lr}, weight_decay 0, clip norm 1, no dropout; batch 1',
        feature_policy='one frozen extraction shared by both arms', test_scored=False,
        budget='matched presentations; 600 optimization seconds/arm excluding diagnostics; report any mismatch',
        limitation='14 shared pitch sources; new raster placements only, not composition-family-disjoint')
    (output / 'config.json').write_text(json.dumps(config, indent=2))
    features = {s:[] for s in samples}
    hashes = {}
    extraction_start = time.perf_counter()
    with torch.no_grad():
        for split, ss in samples.items():
            for sample in ss:
                if args.device == 'mps':
                    torch.mps.empty_cache()
                feature = model.forward_encoder(image_tensor(args.dataset, sample['record'], args.resolution).to(args.device)).permute(0,2,1).contiguous()
                hashes[sample['record']['name']] = hashlib.sha256(feature.cpu().numpy().tobytes()).hexdigest()
                features[split].append(feature)
    (output / 'feature_hashes.json').write_text(json.dumps(hashes, indent=2))
    config['feature_hashes_sha256'] = sha256(output / 'feature_hashes.json')
    config['feature_extraction_seconds'] = time.perf_counter() - extraction_start
    (output / 'config.json').write_text(json.dumps(config, indent=2))
    if getattr(args, 'capacity_comparison', False) or baseline_path:
        config['comparison'] = 'small versus medium; score target only'
        config['versions'] = {'small': {'width': 128, 'layers': 2},
                              'medium': {'width': 256, 'layers': 4}}
        if baseline_path:
            baseline = Path(baseline_path)
            previous = json.loads((baseline / 'config.json').read_text())
            for field in ('dataset_manifest_sha256', 'encoder_weights_sha256',
                          'encoder_config_sha256', 'resolution', 'seed', 'presentations'):
                if previous[field] != config[field]:
                    raise ValueError(f'baseline mismatch: {field}')
            if json.loads((baseline / 'feature_hashes.json').read_text()) != hashes:
                raise ValueError('baseline feature hashes differ')
            config['comparison'] = 'medium lower learning rate versus saved medium baseline'
            config['versions'] = {'medium': {'width': 256, 'layers': 4}}
            config['baseline_config_sha256'] = sha256(baseline / 'config.json')
        config['arms'] = ['score']
        config['initialization_policy'] = 'fresh seed 7 per architecture; different shapes, not identical weights'
        config['feature_policy'] = 'one frozen extraction shared by both capacities'
        (output / 'config.json').write_text(json.dumps(config, indent=2))
        reports = {}
        encoder = model.encoder
        del model
        for name, shape in config['versions'].items():
            torch.manual_seed(args.seed)
            model = make_model(encoder, args.resolution, CAP, **shape).to(args.device)
            initial = trainable_state(model)
            if baseline_path:
                previous_initial = torch.load(baseline / 'medium_initial.pt', map_location='cpu', weights_only=True)
                if initial.keys() != previous_initial.keys() or any(
                        not torch.equal(v, previous_initial[k]) for k, v in initial.items()):
                    raise ValueError('baseline initialization differs')
                config['baseline_initial_tensors_identical'] = True
                initial = previous_initial
            version_initial = output / (name + '_initial.pt')
            torch.save(initial, version_initial)
            config['versions'][name].update(
                trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
                initial_sha256=sha256(version_initial))
            (output / 'config.json').write_text(json.dumps(config, indent=2))
            reports[name] = train_arm(model, initial, features, samples, 'score', args,
                                     output / name, config['steps_per_arm'])
            del model
        left, right = ('medium', 'medium') if baseline_path else ('small', 'medium')
    else:
        reports = {arm:train_arm(model, initial, features, samples, arm, args,
                                 output / arm, config['steps_per_arm']) for arm in ARMS}
        left, right = 'score', 'pitch'
    result = dict(arms=reports, matched_steps=reports[left]['steps'] == reports[right]['steps'],
        matched_order=reports[left]['order_sha256'] == reports[right]['order_sha256'],
        initial_state_sha256=config['initial_state_sha256'], features_shared=True, test_scored=False)
    if baseline_path:
        old = json.loads((baseline / 'medium/result.json').read_text())
        result['matched_steps'] = reports['medium']['steps'] == old['steps']
        result['matched_order'] = reports['medium']['order_sha256'] == old['order_sha256']
        result['baseline'] = str(baseline)
        result['baseline_initial_tensors_identical'] = True
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(completed=True, arms={a:{'selected_step':r['selected_step'],
        'selected_validation':r['controls']['selected']['validation']['totals'],
        'final_validation':r['controls']['final']['validation']['totals']} for a,r in reports.items()})), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'output', 'encoder-weights', 'encoder-config'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--device', choices=('cpu', 'mps', 'cuda'), default='mps')
    parser.add_argument('--capacity-comparison', action='store_true', help='compare fresh 2x128 and 4x256 score decoders on shared features')
    parser.add_argument('--medium-lr-baseline', help='prior capacity run; require identical features and medium initialization')
    parser.add_argument('--lr', type=float, default=.001)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--presentations', type=int, default=300)
    parser.add_argument('--max-train-seconds', type=int, default=600)
    args = parser.parse_args()
    args.resolution, args.width, args.layers = 1024, 128, 2
    if not 0 < args.lr <= .001:
        parser.error('learning rate must be positive and at most .001')
    run(args)
