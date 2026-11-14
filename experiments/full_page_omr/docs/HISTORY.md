# Historical full-page OMR reports

The reports below preserve the design decisions and measured results that led
to the current Humdrum direction. They are historical evidence, not the active
code map or a list of experiments to rerun.

On 2026-11-14 the user requested removing redundant code after committing the
Humdrum move. The following retired components were removed together:

- MusicXML instrumental-part/scenario/jazz generators and their font-coverage
  sheet generator.
- The restricted `musvit-score-v1` tree codec, semantic inspector, fixtures and
  constrained decoding implementation.
- Pilot/clean-page/short-staff/one-note/compact-pitch/placement dataset exporters,
  trainers and associated diagnostics, including earlier target/converter audits.
- Tests specific to those retired components. Generic font-resource, model and
  scan-degradation tests remain, alongside the active application suite.

The full source and tests are preserved in Git commit `1b57dfe` ("Move to **kern").
For example, read an old implementation without changing the current checkout:

```sh
git show 1b57dfe:experiments/full_page_omr/training/overfit_pilot.py
```

Reproducing a historical experiment requires that source/dependency snapshot and
its original local data/configuration; old commands in these reports do not run
against today's tree. Dataset exports, run outputs, scans, annotations and weights
have not been removed or overwritten. Source hashes in existing manifests still
refer to the original implementation. No compatibility wrappers were added.

Reports retain their paths so existing diary links remain valid. Their relative
code links may point to removed files; use the same path with `git show` above.
The earliest original bekern/Lightning implementation was removed previously and
is described in the original-repository links in those reports.

| Retained report |
| --- |
| [Small versus medium decoder — 2026-11-08](CAPACITY_COMPARISON.md) |
| [Clean held-out page baseline](CLEAN_BASELINE.md) |
| [Constrained score decoding — 2026-11-01](CONSTRAINED_DECODING.md) |
| [Controlled dense-page edits — 2026-10-31](CONTROLLED_EDITS.md) |
| [Dense-page learning diagnostic — 2026-10-31](DENSE_OVERFIT.md) |
| [Clean composition diversity experiment — 2026-11-01](DIVERSITY_BASELINE.md) |
| [Music font coverage sheets](FONT_COVERAGE.md) |
| [Longer clean-page development baseline — 2026-10-31](LONG_BASELINE.md) |
| [Medium decoder lower learning rate — 2026-11-08](MEDIUM_LOWER_LR.md) |
| [MusicXML target normalization policy](NORMALIZATION_POLICY.md) |
| [Bounded one-note pitch pilot — 2026-11-06](ONE_NOTE.md) |
| [Clean single-page overfit pilot](OVERFIT_PILOT.md) |
| [All-notes paired output-target comparison — 2026-11-06](PITCH_TARGETS.md) |
| [Placement comparison — 2026-11-08](PLACEMENT_COMPARISON.md) |
| [Score codec prototype](SCORE_CODEC.md) |
| [Short-staff visual transfer experiment — 2026-11-01](SHORT_STAFF.md) |
| [Synthetic horn parts](SYNTHETIC_PARTS.md) |
| [Target-format analysis — 2026-10-31](TARGET_FORMAT_ANALYSIS.md) |

Current work: [pipeline](HUMDRUM_PIPELINE.md), [scope](HUMDRUM_SCOPE.md),
[curriculum design](CURRICULUM_DATASET.md), and [coverage inventory](TARGET_COVERAGE.md).
