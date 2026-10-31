"""Bounded frozen-encoder baseline with validation selection and untouched test scoring."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import resource
import sys
import time
import xml.etree.ElementTree as ET

import editdistance
import torch
from torch import nn
import torch.nn.functional as F

from .clean_page_data import CleanPageDataset
from .overfit_pilot import CachedGreedy, greedy, local_encoder, make_model
from .pilot_data import sha256
from .score_codec import CodecError, PROFILE, VOCABULARY_SHA256, W2I, decode
from .score_semantics import inspect_score


def structural_errors(expected, actual):
    """Only defined for complete, semantically valid scores; no prediction repair."""
    left, right = inspect_score(expected), inspect_score(actual)

    def events(score):
        return [json.dumps((pi, bi, e['onset'], e['duration'], e['voice'], e['staff'], e['pitch'], e['chord']))
                for pi, p in enumerate(score['parts']) for bi, b in enumerate(p['measures']) for e in b['events']]

    gold, predicted = events(left), events(right)
    lroot, rroot = ET.fromstring(expected), ET.fromstring(actual)
    signature = lambda root: [(n.tag, ET.tostring(n, encoding='unicode'))
                              for n in root.findall('.//key') + root.findall('.//time')]
    return dict(event_edit_distance=editdistance.eval(gold, predicted), reference_events=len(gold),
                predicted_events=len(predicted),
                missing_measures=max(0, len(lroot.findall('part/measure')) - len(rroot.findall('part/measure'))),
                extra_measures=max(0, len(rroot.findall('part/measure')) - len(lroot.findall('part/measure'))),
                signatures_equal=signature(lroot) == signature(rroot),
                instruction_words_equal=[n.text for n in lroot.findall('.//words')] == [n.text for n in rroot.findall('.//words')],
                playback_equal=[p['playback'] for p in left['parts']] == [p['playback'] for p in right['parts']],
                full_semantics_equal=left == right)


def prediction_metrics(target, prediction):
    result = dict(exact=target == prediction, reference_tokens=len(target), predicted_tokens=len(prediction),
                  token_edits=editdistance.eval(target, prediction), eos=prediction[-1] == W2I['<eos>'],
                  truncated=prediction[-1] != W2I['<eos>'], valid_score=False, structural=None, error=None)
    xml = None
    try:
        xml = decode(prediction)
        errors = structural_errors(decode(target), xml)
        result.update(valid_score=True, structural=errors)
    except (CodecError, ValueError) as error:
        result['error'] = str(error)
    return result, xml


@torch.inference_mode()
def teacher_metrics(model, features, targets):
    """Gold-prefix diagnostics, explicitly separate from autonomous decoding."""
    model.eval()
    total_loss, correct, count = 0., 0, 0
    for feature, target in zip(features, targets):
        sequence = torch.tensor([target], device=feature.device)
        logits = model.forward_decoder(feature, sequence[:, :-1]).logits
        labels = sequence[:, 1:]
        total_loss += F.cross_entropy(logits, labels, reduction='sum').item()
        correct += (logits.argmax(dim=1) == labels).sum().item()
        count += labels.numel()
    return dict(cross_entropy=total_loss / count, next_token_accuracy=correct / count, tokens=count,
                label='teacher forced; gold prefix supplied, not autonomous transcription')


@torch.inference_mode()
def recognize(model, features, targets, records, output, label):
    model.eval()
    folder = output / label
    folder.mkdir(exist_ok=False)
    results, started = [], time.perf_counter()
    for feature, target, record in zip(features, targets, records):
        prediction = greedy(model, feature, model.maxlen)
        result, xml = prediction_metrics(target, prediction)
        result.update(name=record['name'], kind=record['kind'])
        (folder / f"{record['name']}.json").write_text(json.dumps(dict(tokens=prediction, metrics=result), indent=2))
        if xml is not None:
            (folder / f"{record['name']}.musicxml").write_text(xml)
        results.append(result)
        print(json.dumps(dict(decoded=record['name'], exact=result['exact'], valid=result['valid_score'],
                              token_error=result['token_edits'] / len(target), tokens=len(prediction),
                              seconds=time.perf_counter() - started)), flush=True)
    valid = [r['structural'] for r in results if r['valid_score']]
    summary = dict(count=len(results), exact=sum(r['exact'] for r in results), valid=sum(r['valid_score'] for r in results),
                   eos=sum(r['eos'] for r in results), truncated=sum(r['truncated'] for r in results),
                   token_error=sum(r['token_edits'] for r in results) / sum(r['reference_tokens'] for r in results),
                   structural_scored=len(valid), structural_unscorable=len(results)-len(valid),
                   event_error_valid_only=(sum(r['event_edit_distance'] for r in valid) /
                                           sum(r['reference_events'] for r in valid)) if valid else None,
                   missing_measures_valid_only=sum(r['missing_measures'] for r in valid),
                   extra_measures_valid_only=sum(r['extra_measures'] for r in valid),
                   seconds=time.perf_counter() - started, examples=results)
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


def train(args):
    if min(args.steps, args.eval_every, args.max_tokens, args.max_train_seconds) <= 0:
        raise ValueError('bounds must be positive')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    device = torch.device(args.device)
    if device.type == 'mps' and not torch.backends.mps.is_available():
        raise RuntimeError('MPS requires GPU access; no silent CPU fallback')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    # Test examples are loaded and scored only after training/checkpoint selection.
    data = {s: CleanPageDataset(args.dataset, s, args.resolution) for s in ('train', 'validation')}
    targets = {s: [t.tolist() for _, t in d.samples] for s, d in data.items()}
    if any(len(t) > args.max_tokens for ts in targets.values() for t in ts):
        raise ValueError('target exceeds fixed cap; never truncate labels')
    model = make_model(local_encoder(args.encoder_weights, args.encoder_config), args.resolution,
                       args.max_tokens, args.width, args.layers).to(device)
    model.eval()
    config = dict(vars(args), profile=PROFILE, vocabulary_sha256=VOCABULARY_SHA256,
                  encoder_weights_sha256=sha256(args.encoder_weights),
                  encoder_config_sha256=sha256(args.encoder_config),
                  dataset_manifest_sha256=sha256(Path(args.dataset) / 'manifest.json'),
                  implementation_sha256={p.name:sha256(p) for p in (Path(__file__), Path(__file__).with_name('clean_page_data.py'),
                    Path(__file__).with_name('pilot_data.py'), Path(__file__).with_name('overfit_pilot.py'),
                    Path(__file__).parent/'smt_foundation/modeling_smt.py')},
                  started_utc=datetime.now(timezone.utc).isoformat(), torch=torch.__version__,
                  trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
                  encoder_frozen=True, batch_size=1, dropout=0, augmentation=False,
                  selection='minimum validation teacher-forced cross entropy; test never used for selection',
                  warm_start=None, decoding='unconstrained greedy from BOS; fixed cap independent of each target',
                  resolution_normalization='RGB [0,1], bilinear square resize')
    (output/'config.json').write_text(json.dumps(config, indent=2))

    def cache_images(dataset):
        model.eval()
        with torch.no_grad():
            features = [model.forward_encoder(image.to(device)).permute(0, 2, 1).contiguous()
                        for image, _ in dataset.samples]
        return features

    features = {s:cache_images(d) for s,d in data.items()}
    # Runtime agreement check for the shared incremental decoder implementation.
    with torch.no_grad():
        prefix = targets['train'][0][:16]
        cache = CachedGreedy(model, features['train'][0])
        for pos, token in enumerate(prefix):
            incremental = cache.step(token, pos)
        full = model.forward_decoder(features['train'][0], torch.tensor([prefix],device=device)).logits[0,:,-1]
        torch.testing.assert_close(incremental, full, atol=2e-4, rtol=2e-4)
    initial = {s:teacher_metrics(model,features[s],targets[s]) for s in data}
    (output/'initial_teacher.json').write_text(json.dumps(initial,indent=2))
    print(json.dumps(dict(initial_teacher=initial)),flush=True)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=args.lr,weight_decay=0)
    best_loss, best_step, order = float('inf'), None, []
    history, started = [], time.perf_counter()
    presentations = [0] * len(data['train'])

    def checkpoint(step, path):
        state = {k:v.detach().cpu() for k,v in model.state_dict().items() if not k.startswith('encoder.')}
        torch.save(dict(trainable_state=state,step=step,vocabulary_sha256=VOCABULARY_SHA256,
                        width=args.width,layers=args.layers),path)

    for step in range(1,args.steps+1):
        if not order:
            order = list(range(len(data['train'])))
            rng.shuffle(order)
        index = order.pop()
        model.train()
        model.encoder.eval()
        optimizer.zero_grad(set_to_none=True)
        sequence = torch.tensor([targets['train'][index]],device=device)
        logits = model.forward_decoder(features['train'][index],sequence[:,:-1]).logits
        loss = F.cross_entropy(logits,sequence[:,1:])
        if not torch.isfinite(loss):
            raise RuntimeError('nonfinite loss')
        loss.backward()
        nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.)
        optimizer.step()
        presentations[index] += 1
        value = loss.item()
        del logits,loss
        history.append(value)
        if step == 1 or step % 25 == 0:
            message = dict(step=step,loss=value,mean_recent_loss=sum(history[-25:])/len(history[-25:]),
                           seconds=time.perf_counter()-started)
            with (output/'training.jsonl').open('a') as stream:
                stream.write(json.dumps(message)+'\n')
            print(json.dumps(message),flush=True)
        timed_out = time.perf_counter()-started >= args.max_train_seconds
        if step % args.eval_every == 0 or step == args.steps or timed_out:
            validation = teacher_metrics(model,features['validation'],targets['validation'])
            item = dict(step=step,validation=validation,seconds=time.perf_counter()-started)
            with (output/'validation.jsonl').open('a') as stream:
                stream.write(json.dumps(item)+'\n')
            print(json.dumps(item),flush=True)
            checkpoint(step,output/'last.pt')
            if validation['cross_entropy'] < best_loss:
                best_loss,best_step = validation['cross_entropy'],step
                checkpoint(step,output/'best.pt')
        if timed_out:
            break
    training_seconds = time.perf_counter()-started
    # Separately diagnose learning at the final update; this never selects weights.
    last_train_sample, last_validation, last_teacher = None, None, None
    if args.evaluate_last:
        last_teacher = {s:teacher_metrics(model,features[s],targets[s]) for s in data}
        last_train_sample = recognize(model,features['train'][:3],targets['train'][:3],
                                      data['train'].records[:3],output,'last_train_sample')
        last_validation = recognize(model,features['validation'],targets['validation'],
                                    data['validation'].records,output,'last_validation')
    state = torch.load(output/'best.pt',map_location='cpu',weights_only=True)['trainable_state']
    loaded = model.load_state_dict(state,strict=False)
    if loaded.unexpected_keys or any(not k.startswith('encoder.') for k in loaded.missing_keys):
        raise ValueError('incompatible selected checkpoint')
    model.eval()
    final_teacher = {s:teacher_metrics(model,features[s],targets[s]) for s in data}
    (output/'final_teacher.json').write_text(json.dumps(final_teacher,indent=2))
    # Three preregistered training examples (one per instrument) assess whether
    # training pages themselves can be transcribed; all held-out pages are scored.
    evaluation = {'train_sample':recognize(model,features['train'][:3],targets['train'][:3],
                                          data['train'].records[:3],output,'train_sample')}
    evaluation['validation'] = recognize(model,features['validation'],targets['validation'],
                                        data['validation'].records,output,'validation')
    if not args.skip_test:
        test = CleanPageDataset(args.dataset,'test',args.resolution)
        test_targets = [t.tolist() for _,t in test.samples]
        if any(len(t) > args.max_tokens for t in test_targets):
            raise ValueError('test target exceeds fixed cap')
        test_features = cache_images(test)
        final_teacher['test'] = teacher_metrics(model,test_features,test_targets)
        evaluation['test'] = recognize(model,test_features,test_targets,test.records,output,'test')
    (output/'final_teacher.json').write_text(json.dumps(final_teacher,indent=2))
    report = dict(steps=step,selected_step=best_step,training_seconds=training_seconds,
                  last_train_sample=last_train_sample, last_validation=last_validation,
                  last_teacher=last_teacher, test_scored=not args.skip_test,
                  presentations_per_page=dict(zip([r['name'] for r in data['train'].records],presentations)),
                  time_bound_reached=timed_out,initial_teacher=initial,final_teacher=final_teacher,evaluation=evaluation,
                  peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform=='darwin' else 1024),
                  mps_driver_allocated_bytes=torch.mps.driver_allocated_memory() if device.type=='mps' else None,
                  encoder_frozen=all(not p.requires_grad and p.grad is None for p in model.encoder.parameters()),
                  limitation='small clean synthetic distribution, not real scans or full notation coverage')
    (output/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(completed=True,steps=step,selected_step=best_step,training_seconds=training_seconds,
                          evaluation={s:{k:v for k,v in r.items() if k!='examples'} for s,r in evaluation.items()})),flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--encoder-weights',required=True)
    parser.add_argument('--encoder-config',required=True)
    parser.add_argument('--device',choices=('mps','cpu','cuda'),default='mps')
    parser.add_argument('--resolution',type=int,default=1024)
    parser.add_argument('--max-tokens',type=int,default=8192)
    parser.add_argument('--steps',type=int,default=1200)
    parser.add_argument('--eval-every',type=int,default=200)
    parser.add_argument('--max-train-seconds',type=int,default=900)
    parser.add_argument('--width',type=int,default=128)
    parser.add_argument('--layers',type=int,default=2)
    parser.add_argument('--lr',type=float,default=.001)
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--skip-test',action='store_true',help='Development run: do not load or score test targets')
    parser.add_argument('--evaluate-last',action='store_true',help='Also diagnose training/validation at the final update, without selecting it')
    train(parser.parse_args())
