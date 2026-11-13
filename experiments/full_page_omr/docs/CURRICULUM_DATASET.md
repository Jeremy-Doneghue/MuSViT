# Full-size OMR curriculum and scan dataset

2026-11-14 implementation update: new [Curriculum Lab previews](HUMDRUM_PIPELINE.md)
are authored directly in Humdrum, with SVG/MEI/raster derived by Verovio. MusicXML
is optional at import/editor boundaries. Earlier source/target implementation
recommendations below are historical; new tokenizer/training work must use the
selected canonical Humdrum direction.

2026-11-14 update: use the selected [Humdrum recognition scope](HUMDRUM_SCOPE.md)
for the next model target, retaining MusicXML sources/editor interchange. First
milestone includes pitched parts, piano, percussion, common dynamics and
performance text, with omissions flagged. Target conversion/fidelity work now
precedes the earlier MusicXML-target implementation sequence below. The model,
scan-calibration and grouped-data proposals remain relevant; no new training is
queued by this update.

Design recorded 2026-11-08. The user selected a move toward the full-size
paper-based OMR model and curriculum/dataset work, with real scans as the target.
The recipes, quantities and gates below are proposals, not executed experiments.

2026-11-13 update: the user selected retaining MusicXML and defining explicit
normalization/omission decisions. See [the policy and executed codec audit](NORMALIZATION_POLICY.md).
Apply the resulting target normalization before freezing a new training export;
existing early datasets/checkpoints need no compatibility/migration work. The
full-model and scan-calibration proposals below remain relevant, but do not
assume the current v1 target already satisfies the new policy.

## Evidence and model choice

The medium decoder at lr .0001 learned all training images. Increasing placement
diversity improved selected validation from 25/56 to 48/56 for seed 7 and from
13/56 to 48/56 for seed 19. This supports appearance diversity. It does not isolate
a capacity benefit: the matched small/medium comparison at .001 failed, and there
is no matched small .0001 result. Moving to the full decoder is a reasonable
engineering choice supported by the published approach, not a proven local
scaling law. See [placement results](PLACEMENT_COMPARISON.md).

Retain the verified MuSViT Base encoder. The
[upstream decoder configuration](https://github.com/OMR-PRAIG-UA-ES/MuSViT/blob/main/experiments/full_page_omr/smt_foundation/configuration_smt.py)
defaults to eight layers, width 256, feed-forward width 256; its
[implementation](https://github.com/OMR-PRAIG-UA-ES/MuSViT/blob/main/experiments/full_page_omr/smt_foundation/modeling_smt.py)
uses four attention heads and dropout .1. These are inspected upstream defaults,
not a verified record of every setting in the authors' training run.
Our pilot factory instead sets feed-forward width to twice the model width and
disables dropout. Merely selecting eight layers there would not restore these
defaults. Introduce an explicit new preset without changing historical presets.

Keep `musvit-score-v1` initially, and audit coverage before expanding the corpus.
This remains an adaptation, not an exact paper reproduction: our targets and
dataset differ from the original bekern setup. Check full-page token lengths,
memory, runtime and cache/full-prefix agreement before committing a large budget.
Never truncate targets to fit. Use .0001 as a starting decoder learning-rate
candidate based on local evidence, not as an established full-model optimum.

The [paper, A.9.1](https://arxiv.org/html/2606.31811v1#A9.SS1) starts OMR training
with synthetic pages of increasing system count, then gradually mixes real pages
with synthetic examples. The encoder stays frozen during synthetic training;
the fine-tuning version unfreezes it at the real-page stage. Adopt this broad
schedule, with a brief local recognition check rather than an indefinite one-note
prerequisite. Encoder adaptation requires new feature extraction during training;
cached frozen features cannot support it.

## Two independent difficulty dimensions

Musical complexity and image damage must be sampled separately. Teach a notation
feature on clean/lightly degraded examples before testing it under stronger damage.
Retain clean examples throughout; do not make every late-stage page badly damaged.

| Stage | Musical content and layout | Appearance and evaluation |
| --- | --- | --- |
| 0: integration check | Known one-note fixtures and short complete bars, all intended basic labels taught | Existing placement diagnostics; full decoder learning, validity and image conditioning; bounded smoke run |
| 1: readable passages | New 1–4 bar sequences; pitches, rests, durations, accidentals, dots and beams; valid meter/pickups | Realistic staff scale, varied placement/spacing/fonts, clean and mild scan effects; held-out sequences/families |
| 2: systems and pages | Increase system count; clefs/keys/meters and changes; ties, slurs, dynamics, text | Vary margins, density and breaks; moderate scan mixtures; assess errors by scale and system count |
| 3: collection coverage | Piano chords/voices, percussion, jazz articulations, chord symbols/slashes, repeats/endings, multibar rests, navigation | Focused examples plus ordinary passages; preserve notation and text attachment; introduce combinations after constituent coverage |
| 4: real-scan adaptation | Verified transcriptions of actual parts; replay synthetic and earlier examples | Mix real training scans progressively; compare frozen versus adapted encoder; retain real development and locked test sets |

Include simple piano and percussion examples early enough to avoid a horn-only
training distribution; stage 3 expands their complexity. Handwriting is a distinct
source/style dimension: dirty engraving or a handwritten-looking font does not
establish handwritten recognition. Multi-page context and part assembly need an
explicit contract beyond the current complete single-page exporter.

Starting sampling proposal: stage 1 uses 50% clean, 40% mild and 10% moderate
appearance; later synthetic stages use 30% clean, 40% mild, 30% moderate. Retain
20% earlier-stage musical examples when advancing. These are initial sampling
weights, not measured scan frequencies; revise using development evidence.
Heavy damage initially belongs in a separately reported stress set.

## Dataset composition and splits

Use three complementary sources: controlled synthetic compositions for balanced
features; audited real compositions re-engraved to diversify musical structure;
and actual scans with verified labels for domain adaptation and evaluation.
PDMX is a candidate for the second source, pending the existing compatibility,
provenance and family audit. No corpus download is implied by this design.

Assign composition/arrangement families to splits before excerpting, engraving
or augmentation. All parts, pages, excerpts, renderings, crops and scans from a
family stay together. Also report a scan-source/edition holdout where feasible.
Do not count variant images as independent compositions. The old shared-source
placement diagnostic remains a smoke test, not the new dataset's generalization
benchmark. Audit unsupported notation and font fallback before selecting examples;
record exclusions rather than silently simplifying labels.

Proposed first calibration inventory: 30–50 real development pages across at
least ten composition families, varied print/scan sources, single staves, piano
and percussion. This is for profile calibration and failure discovery, not a
statistically strong final benchmark. Reserve separate source families for a
locked test set before tuning. Start transcription with complete short passages
and verified context, then annotate full pages; do not invent reference labels
from an unverified model prediction. Existing visually reviewed references are
development material, not pristine test data.

For the first training export, target roughly 1,000 distinct short-passage
families and at least 100 held-out validation families, with balanced constituent
symbols and novel sequences. Final counts follow coverage and token-cost audits;
these are planning quantities, not a launch contract. Split all future stage
families globally so longer examples cannot leak earlier validation passages.

## Augraphy: calibrate scan mechanisms and protect notation

Current [scan tooling](../../scan_degradation/README.md) supplies accepted
`light-copy` and `library-scan` starting appearances. The latter fixes rotation
at -1 degree and has no source-to-output coordinate mapping. Neither preset has
an OMR accuracy result. Previously rejected worn/custom noise stays retired.
Augraphy's [ink/paper/post processing model](https://augraphy.readthedocs.io/en/latest/doc/source/how_augraphy_works.html)
is a useful organization for candidate effects; defaults are not music-specific
calibration. Candidate implementation/classes must be checked against the installed
version before introducing new profiles.

| Mechanism | Candidate variation | Music-specific review |
| --- | --- | --- |
| Framing and geometry | Margins, dark scanner edges, small skew; later gentle warp if observed | All staves and required context remain visible; staff-relative pitch preserved |
| Resolution and focus | Raster DPI, resampling, mild blur, compression | Dots, ledger lines, flags and adjacent beams remain distinguishable at encoder input size |
| Ink/copying | Local fading, limited ink spread/dropout, uneven contrast | Preserve accidental identity, open/filled noteheads, ties and rest counts |
| Paper and lighting | Uneven background, edge shadow, restrained texture | Match development scans rather than adding conspicuous uniform noise |
| Structured interference | Bleed-through, folds, stamps or pencil marks where observed | Separate artifacts from intended written annotation; reject changed/ambiguous targets |

Build coherent scan profiles rather than independently activating every effect:
for example, a faint photocopy, a clean scan with skew/dark borders, or a blurred
low-resolution copy. Randomize edge position and orientation rather than teaching
one fixed right-edge/-1-degree cue. Start with one mechanism at a time and add
plausible combinations after review. Express severity relative to staff spacing
and line thickness as well as source pixels; a fixed blur kernel at different DPI
does not represent the same damage.

Render at sufficient resolution, apply paper/ink/scan effects in a declared order,
then perform the actual model resizing. Inspect both full-page appearance and
critical symbol crops after the final 1024-input preprocessing. A realistic-looking
300-DPI preview may lose its dots and accidentals during downsampling. Measure
effective staff spacing and smallest symbol sizes for every stage.

Routine training augmentation must preserve readable target evidence. If damage
erases a distinguishing dot/accidental, do not automatically keep the original
exact target as an ordinary supervised pair. Exclude it or mark it for the future
explicit ambiguity/reconstruction task. Clipped-but-inferable notation remains a
required coverage case, but its supervision policy is still open. Geometry-only
changes can retain sequence labels when complete content/context survives;
spatial labels require a verified transformation. Nonlinear transforms require
more than a single affine matrix.

Initially export finite, reviewed variants into new immutable directories. This
supports reproducibility and feature caching. Cache by the final image hash plus
encoder/preprocessing identity: every altered image requires its own features.
Online random augmentation later needs recomputation or a bounded variant cache.
The existing global RNG/JIT wrapper is sequential, not thread-safe; do not place
it in concurrent threads unchanged.

Record source/family/split, notation coverage, clean image and target hashes,
renderer/font/version, raster and final dimensions, preprocessing, profile/version,
effect order/parameters, all seeds, library versions, variant hash, geometry
mapping availability and legibility review. Keep labels and images in ignored
artifacts; documentation contains contracts, paths and summary evidence only.

## Evaluation and first implementation sequence

Maintain separate panels: clean unseen families, paired degraded variants of
those families, unseen degradation combinations, and actual real scans. Score
printed and handwritten material separately. Report sequence edit error, semantic
validity/EOS/truncation, aligned pitch/rhythm/rest accuracy, voice/staff relations,
rare-feature errors and exact bars/pages. Invalid predictions count as failures;
do not report only the valid subset. Our token SER is not directly comparable
with the paper's bekern SER. Use family-level uncertainty estimates because
variants are correlated.

For short passages, proposed progression criteria are >=99% semantic validity,
>=99% joint pitch/duration accuracy and >=95% exact passages on at least 100
held-out families, with image-conditioning checks and a second seed confirmation.
Fix how insertions/deletions/invalid outputs are counted before launch. These are
engineering targets, not demonstrated performance or universal full-page gates.
For longer pages, use per-feature error and rare-feature coverage alongside exact
pages; predeclare stage-specific criteria rather than silently weakening gates.

First compare clean-only versus clean-plus-reviewed-Augraphy training with the
same full decoder, source families, optimization budget and evaluation. Judge
augmentation primarily by real-development improvement while monitoring clean
regressions. Synthetic robustness alone is insufficient. Tune on development
only; report the locked test once the recipe is fixed. Later compare curriculum
against mixed-complexity training at comparable compute.

Next concrete work: implement the explicit full decoder preset and a bounded
integration check; assemble a source-grouped scan calibration manifest and a
clean/mild/moderate contact sheet from representative synthetic notation. Review
legibility at actual model resolution, then freeze the first short-passage export
contract and compute budget. No new training, annotation, data export or model
configuration change has been executed as part of this design note.
