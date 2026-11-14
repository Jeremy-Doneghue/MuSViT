# Short-staff visual transfer experiment — 2026-11-01

> Historical report: the MusicXML-target implementation described here was
> retired on 2026-11-14. Commands and relative source links below describe the
> code at Git commit `1b57dfe`, not the current executable pipeline. See the
> [historical index](HISTORY.md) for retrieval and the
> [current pipeline](HUMDRUM_PIPELINE.md) for ongoing work. Results below are
> retained as recorded; this cleanup did not rerun these experiments.


Status: bounded MPS run and both checkpoint controls completed; transfer gate failed.
User approved setting up the diagnostic after review of DIVERSITY_BASELINE.md.

## Question and scope

Can the current frozen encoder and small decoder read unseen short passages,
including controlled note edits, without memorizing complete training scores?
This isolates a simpler recognition problem before further full-page scaling.
Keep musvit-score-v1, RGB input, frozen encoder, and the existing training code.
It is not an encoder ablation or proof about real scans, handwriting or polyphony.

## Fixed dataset

`outputs/short_staff_20261101_01/`, recipe `short-staff-v1`, seed 113:

- 96 independent training families, one passage each.
- 16 independent validation families, each with base/pitch/rhythm versions:
  48 records, **16 independent families**, not 48 independent compositions.
- No test export or test scoring. Existing full-page test data is untouched.
- Two bars on one staff, treble clef, C major, 4/4, eight notes total. Natural
  pitches sampled uniformly from C4–B5; realized pitch counts are in the manifest.
  Every bar permutes eighth, eighth, quarter and half notes. Duration coverage is
  exactly 50% eighths, 25% quarters, 25% halves; pitch coverage is approximate.
- Pitch probe changes one note by one diatonic step. Rhythm probe exchanges two
  unequal durations in one bar, keeping pitches and bar fill fixed. Edited
  position is seeded and varies by family. All variants remain with their parent.
- No rests, accidentals, ties, dynamics, chords, multiple voices, or meter changes.
  This is deliberately narrow. Rhythm-count and length generalization are absent.
- A square white page contains one system near the top, keeping the current
  square input path and a fixed engraving scale. No tight cropping, augmentation,
  or positional/layout generalization claim. Horizontal note positions vary with
  engraving/rhythm; staff position remains fixed.

Export checks complete score round trips, rendered measure presence, exactly one
system, token cap and cross-split source/family/event-fingerprint/target/raster
separation. Fingerprints also reject simple transpositions across splits.
Exports refuse overwrite. Source hashes and renderer options/version are recorded.

All 144 targets contain 459 tokens, below the independently fixed 1536 cap.
An additional setup audit loaded both splits, verified 432 artifact hashes and
round trips, and saved `setup_audit.json`. One validation raster was visually
inspected. Verovio warns about encoded breaks with no explicit breaks; all
rendered examples passed the single-system and measure-presence assertions.

## Training and evaluation contract

Fresh adaptor/decoder, seed 7; original frozen encoder; width 128, two decoder
layers; 1024 RGB, batch size 1, AdamW lr .001, no dropout or augmentation.
Bound: **9600 updates or 1800 training-loop seconds**, whichever occurs first.
Full completion gives 100 presentations per training passage. Validation every
400 updates. Initialization, final decoding and controls are outside this bound.

Retain minimum validation gold-prefix CE selection for comparability; separately
report selected and final checkpoints. Do not interpret CE as recognition.
Unconstrained greedy decoding starts from BOS and uses the fixed 1536-token cap,
never reference length. No semantic repair, grammar constraints or encoder tuning.

The wrapper runs the existing trainer, then evaluates both checkpoints:

- Autonomous validity, EOS, exactness and token errors on all validation records
  and the trainer's first three training passages.
- Full pitch (step, alteration, octave), duration and joint-event edit counts by
  measure. Counts include sequence insertions/deletions. Missing/extra note counts
  are net count differences per measure, not a uniquely inferred error alignment.
- Positional pitch/duration/joint correctness only for equal-note-count measures;
  report aligned-note and valid-score coverage. Invalid scores are unscorable,
  never repaired or silently counted as zero error. Summaries separate variants.
- All-three-exact family count tests response to both controlled edits.
- Autonomous image swaps rotate across different validation families with the
  same variant type; report agreement with original targets and donor targets.
- Matched/swapped gold-prefix field accuracy and CE, including step, octave and
  duration fields separately. Full reports retain sample counts and field deltas.
- Training-marginal mode baseline supplies reference event slots: it is a field
  prior, not an autonomous recognizer. On the exported validation set it gets
  full pitch 8.854% and duration 50%. Gold prefixes can supply stronger priors;
  image swaps and autonomous edited-pair results are therefore essential controls.

Results live under the training run, with extra controls in
`transfer_controls/result.json`. Evaluation rechecks input hashes and checkpoint
identity. It refuses to overwrite its output. The wiring test uses a tiny random
encoder and forced EOS to verify invalid-output handling; it is not a learning run.

## Decision criteria declared before training

Treat the selected checkpoint as primary and final as a separately reported
optimization diagnostic. A useful initial transfer gate is at least 15/16 valid
base passages, at least 90% positional full-pitch and duration accuracy on the
valid base passages (report denominator/coverage), and at least 12/16 families
exact on all three versions. Additionally require a clear matched-image advantage
in musical-field diagnostics and donor-following autonomous swaps; exactness
without image sensitivity is insufficient. These are engineering gates, not
statistical guarantees or a benchmark claim.

If transfer passes, extend to longer systems and then pages, with paired piano
staves/voices explicitly reintroduced. If it fails despite training success,
compare bounded encoder adaptation on this same task. If training also fails,
inspect optimization/visual feature access first. Do not automatically launch
another run, change format or unfreeze the encoder. Multiple seeds and broader
held-out coverage would be needed before adopting an architecture change.

## Reproduction

Run from the repository root. Existing output paths must remain untouched.

```sh
source experiments/full_page_omr/outputs/studio_setup_20261031/activate_rendering.sh
.venv/bin/python -m experiments.full_page_omr.training.short_staff_experiment train \
  --dataset experiments/full_page_omr/outputs/short_staff_20261101_01 \
  --output experiments/full_page_omr/outputs/short_staff_mps_20261101_01 \
  --encoder-weights model.safetensors \
  --encoder-config experiments/full_page_omr/outputs/studio_setup_20261031/encoder/config.json \
  --device mps
```

For a new immutable dataset export:

```sh
.venv/bin/python -m experiments.full_page_omr.datasets.short_staff_data \
  --output experiments/full_page_omr/outputs/short_staff_NEW
```

If training completed but controls did not start, run
`short_staff_experiment evaluate --run <training run>` using the module invocation.
A partial existing `transfer_controls` directory must be preserved and relocated
before rerunning controls; do not overwrite it.

## Setup checks

Full suite: 79 tests, 78 passed and one sandbox MPS skip. This includes new
round-trip/edit assertions across 20 seeds, split/adapter/tamper/no-overwrite
checks, and a one-update CPU integration test with a tiny synthetic encoder and
forced-EOS decoding through training and both checkpoint evaluations. CLI help
and independent export audit passed. No production training or GPU run executed.

## Executed result — 2026-11-01

User requested execution. Run `outputs/short_staff_mps_20261101_01/` completed
all 9600 updates, exactly 100 presentations per training passage, in 106.456
training/validation/checkpoint seconds. Initialization and autonomous controls
are additional. No time cap hit. Selected update 3200. Original encoder frozen,
test scoring disabled, recipe unchanged. Process exited successfully.
Log: `/private/tmp/musvit-short-staff-training-20261101.log`.

| Outcome | Selected, 3200 | Final, 9600 |
| --- | --- | --- |
| Sampled training valid / exact | 0/3 / 0/3 | 0/3 / 0/3 |
| Training sample token error | 2.760% | 2.905% |
| Validation valid / exact | 0/48 / 0/48 | 0/48 / 0/48 |
| Base / pitch-edit / rhythm-edit valid | 0/16 each | 0/16 each |
| All-three-exact families | 0/16 | 0/16 |
| Validation token error | 3.440% | 3.958% |
| Swapped-image error against original targets | 4.857% | 4.226% |

All 198 autonomous outputs (training samples, matched validation and swaps)
reached EOS, with no token-cap termination. Matched validation failures:
selected 43 duration/type disagreements and five under/overfilled measures;
final 42 duration/type disagreements and six under/overfilled measures.
No complete valid predictions: autonomous full-pitch/duration/event metrics and
re-engraving remain unavailable, not zero-error. Low token error mostly reflects
correct predictable structure and must not be equated with musical accuracy.

Gold-prefix field accuracy on 384 validation notes (48 related passages):

| Field | Selected matched | Selected swapped | Final matched | Final swapped |
| --- | --- | --- | --- | --- |
| Pitch step | 22.14% | 13.80% | 17.97% | 12.50% |
| Octave | 62.24% | 44.53% | 52.86% | 55.47% |
| Duration value | 63.02% | 36.20% | 50.26% | 44.01% |

These are separate next-token fields under gold prefixes, not full-pitch or
joint-note accuracies. In particular, do not compare pitch-step accuracy directly
with the 8.854% full-pitch marginal baseline. The duration mode baseline is 50%.
The selected checkpoint shows meaningful musical-field sensitivity to images,
particularly rhythm, but remains a poor recognizer. The final checkpoint is worse
on matched fields; the result does not support simply extending this recipe.

Autonomous swaps reproduce the donor image's own matched prediction 48/48 at
both checkpoints, changing the recipient prediction 48/48 selected and 47/48
final. This is image-dependent output, **not correct donor transcription**:
none matches the donor's reference score exactly. This distinction is stronger
than merely observing tiny aggregate CE changes, but does not establish reading.

The preregistered transfer gate failed. Because sampled training also fails,
this is not a clean held-out generalization gap. Next proposed action: inspect
optimization and spatial visual-feature access on this short task, using a
localized pitch/rhythm probe or a tightly controlled training-path ablation.
Encoder adaptation remains a candidate, not an established fix or queued run.
Do not move directly to longer systems/pages or launch more training unchanged.

Verification: recomputed all 198 saved autonomous prediction metrics; checked
checkpoint/input hashes, recipe bounds, exact exposure counts, per-example
musical unscorability, family-disjoint donors and swap/donor output consistency.
Saved `independent_audit.json` under the run; audit script/log in
`/private/tmp/musvit-audit-short-staff.py` and
`/private/tmp/musvit-short-staff-audit.json`. Gold-prefix fields were read from
executed GPU diagnostics, not independently rerun. Peak training-process RSS
3,016,916,992 bytes; this does not measure peak memory in later controls.
No source code changed during execution; existing 79-test setup suite remains
the latest regression check. Actual GPU training and cached/full-prefix agreement
passed. No additional experiment queued.
