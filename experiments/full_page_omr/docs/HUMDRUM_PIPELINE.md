# Direct Humdrum preview pipeline

Implemented 2026-11-14 after the user selected Humdrum as canonical source and
model-target direction, with SVG/MEI derived through Verovio. MusicXML is optional
at import/editor-export boundaries; it is not used by the active Curriculum Lab
synthetic preview path.

```text
seed + example → directly authored Humdrum (source.krn)
                         │
                         └→ Verovio → source.svg → raster → scan recipe/model resize
                                   └→ source.mei
```

The desktop source pane displays the exact `source.krn` belonging to the displayed
image; pending control changes do not regenerate/relabel an older preview. Text
includes **kern spines, **dynam spines, interpretation rows, reference records and
notation-bearing layout comments. The web lab exposes the same read-only source.
Real scans have no synthetic score label. Old MusicXML-only previews can still be
opened as saved assets; the source pane requests regeneration rather than silently
converting their labels with a known-lossy converter.

## Implementation

- [humdrum_scores.py](../generation/humdrum_scores.py): pure seeded source
  generators, fixed generated syntax/order, source expectations and direct Verovio
  rendering. No MusicXML parser, score-tree codec, pilot exporter or torch import.
- `apps/bar_review/curriculum.py`: shared desktop/web previews, source fingerprint,
  checksum-verified reuse and immutable export. Warm workers preload the new
  generation module instead of MusicXML dataset modules.
- Preview files: `source.krn`, derived `source.svg` and `source.mei`, native and
  1024 source/augmented PNGs, manifest. ZIPs and portable `.musvitlab` projects
  contain the exact artifacts and their checksums.

All eight existing example selections now use new direct Humdrum compositions:
seeded one-note, two-bar melody, 24-bar horn/piano/drum pages, focused piano voices,
fixed cross-staff beam and focused drums. These are not conversions of the earlier
MusicXML compositions; source fingerprints change and existing exports are not
rewritten. Seeded percussion changes kick placement; cross-staff remains fixed.

Piano sources include chord tones in ascending written pitch order, independent
upper-staff voices via split/merge rows, **dynam and native `*ped`/`*Xped` records.
Drum sources include unpitched markers, x notehead comments, independent rhythmic
voices and two attached passage instructions. Pitched melodies include a standard
dynamic and passage instruction. Text comments immediately precede their target
notes after structural interpretations; placing them before a split can lose the
attachment in this importer. No 32nd-note cutoff was added.

Rendering requires one complete page and verifies expected note/rest/measure/staff
and pedal counts, exact instruction text presence and cross-staff assignment
presence in derived MEI. These checks are safeguards for these generators, not a
complete musical equivalence validator. Derived files normalize renderer-only IDs
and local references, unordered glyph definitions and formatting whitespace so
repeated outputs have stable checksums. The canonical Humdrum source is unchanged
by that output stabilization. Original data/labels/weights are not documentation.

## Checks and limits

Run the focused checks from the repository root:

```sh
MPLCONFIGDIR=/private/tmp/musvit-matplotlib PYTHONPATH=apps/bar_review \
.venv/bin/python -m unittest discover -s apps/bar_review -p 'test_humdrum.py' -q
```

The native test runs in a bounded subprocess. It renders all eight sources, checks
exact source/artifact hashes, tests percussion x heads and two cross-staff note
assignments, changes among Leipzig/Bravura/Petaluma, verifies replay/reuse, checks
ZIP inclusion and restores the three source/derived artifacts into an empty
project directory. An import guard rejects use of the old MusicXML dataset/codec
modules during the native path. Other desktop tests verify source/image ownership,
scrolling and project restoration. See the diary for dated full-suite results.

This implements a **generated-source preview profile**, not canonicalization of
arbitrary Humdrum corpora. It does not implement a new trained decoder, vocabulary,
training adapter or broad corpus export. Earlier MusicXML-tree trainers remain
historical experiment tools and must not be presented as Humdrum trainers.

The selected broader [recognition scope](HUMDRUM_SCOPE.md) still needs fixtures for
hairpins, transposing instruments, accidentals/tuplets beyond these examples,
complex navigation, jazz notation and arbitrary imported scores. Existing old
fixtures and source annotations remain available as historical checks; the native
examples do not establish complete collection coverage or real-scan accuracy.
MEI is an available derived export, not proof of editor interoperability. No new
training run or dataset batch was launched. Next: validate the remaining scoped
notation, then define a deterministic Humdrum tokenizer and bounded training
adapter using the actual canonical source strings.
