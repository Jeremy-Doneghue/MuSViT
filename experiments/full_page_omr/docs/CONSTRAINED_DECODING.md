# Constrained score decoding — 2026-11-01

User approved implementing constrained decoding after the 180-page diversity
experiment. This applies incremental parsing to our existing codec, following
the general idea of [PICARD](https://aclanthology.org/2021.emnlp-main.779/).
It is a local implementation, not a dependency on the SQL PICARD package.

## Contract

`constrained_decoding.ScoreGrammar` exposes `allowed_tokens()` and `consume()`.
Its rules come from the codec's fixed profile, never training/validation target
statistics. Shared required-field, repetition and order tables were factored out
of existing validators without changing their behavior or the vocabulary.

The parser restricts BOS/profile/root/EOS order, nesting, supported child and
attribute names, sorted unique attributes, required fields, child order and
repetition, text placement, literal-vs-byte encoding, UTF-8/XML characters,
enumerated values and numeric value termination. Local completed fields use
`score_semantics._fields` validation. Arbitrary Unicode text remains supported.

`constrained_greedy` uses the existing incremental decoder logits and chooses
the highest-scoring legal token. It records how often the original argmax was
blocked. It does not backtrack, repair predictions, force closures at the cap,
or derive stopping rules from reference scores. Nonfinite/no-legal-token states
are explicit failures; incomplete outputs remain available for inspection.
Unconstrained greedy decoding remains unchanged.

This is a grammar/field constraint, **not full semantic validation**. It does not
track measure timing, voice overlap, span/navigation references, canonical ID
assignment, minimal divisions, or image fidelity. The unchanged codec still
judges full validity. A grammar-complete output can fail codec validation, and
an unfinished scalar/structure can reach the original token cap.

## Declared comparison

Evaluation only, no training or test loading. Run both the validation-selected
(update 11200) and final (14400) checkpoints from
`outputs/clean_diversity180_mps_20261101_02/` on the same six validation images.
Compare against saved unconstrained predictions, independently recomputing their
metrics. Verify dataset, encoder and checkpoint hashes. Preserve original runs.
Use the same resolution, frozen encoder and fixed 8192-token cap.
No target tokens or lengths are passed to the constrained decoder.

Output: `outputs/constrained_diversity180_20261101_01/`.
Log: `/private/tmp/musvit-constrained-eval-20261101.log`.
Report grammar completion and full codec/semantic validity separately, plus EOS,
exactness, token error, intervention count and valid-output structural metrics.
The saved baseline's timing is not a controlled decoding-speed comparison.

```sh
.venv/bin/python -m experiments.full_page_omr.diagnostics.constrained_experiment \
  --run experiments/full_page_omr/outputs/clean_diversity180_mps_20261101_02 \
  --output experiments/full_page_omr/outputs/constrained_NEW --device mps
```

Use a new output directory. MPS execution needs GPU access outside the sandbox.
The recipe above was declared before scoring; executed results follow.


## Executed comparison

Both checkpoints completed all six pages on MPS. All 12 constrained predictions
reached EOS and completed the grammar, with 23 total interventions. No reference
length stopping, target-conditioned choices, repairs, training or test scoring.

| Checkpoint | Unconstrained token error | Constrained token error | Constrained grammar complete | Full valid scores, before → after |
| --- | --- | --- | --- | --- |
| Selected, update 11200 | 31.407% | 45.280% | 6/6 | 0/6 → 0/6 |
| Final, update 14400 | 20.827% | 23.368% | 6/6 | 0/6 → 0/6 |

Exact scores remain 0/6 for each checkpoint. All baselines also reached EOS.
Interventions: 11 selected, 12 final. A small number of changed tokens can alter
many subsequent predictions. Grammar constraints did not improve token accuracy
here and cannot be presented as a recognition improvement.

Independent audit replayed all 12 outputs through the parser, reconstructed XML,
validated the profile tree and local fields independently, and recomputed all
saved token/semantic metrics. `independent_audit.json` records the checks. The
remaining full-validator errors are duration/type disagreements, backup before
measure start, and measure under/overfill. No complete valid predictions exist,
so structural musical errors are unscorable and no re-engraving was attempted.

Tests: 76 ran, 75 passed, one sandbox MPS skip. Controlled-logit tests prove
masking rejects illegal argmax choices and preserves legal sequences; the real
GPU evaluation exercised both saved checkpoints. All existing codec fixtures and
dense horn/piano/drum sequences remain accepted. CLI, compilation and whitespace
checks passed. No datasets or weights overwritten; no commit made.

Keep this decoder opt-in. The next proposed training experiment remains a bounded
longer run on the existing 180 pages, preserving both unconstrained and constrained
evaluation. Duration/voice-position constraints are a separate possible extension;
this result does not establish that they would improve visual recognition.
