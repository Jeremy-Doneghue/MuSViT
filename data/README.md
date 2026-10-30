# Shared reference data

`reference_parts/` contains the existing real-part PDF and MusicXML reference
files used for OMR development and scan-degradation comparisons. They were moved
from `resources/exampleparts/`; neither file was regenerated or altered.

These are manually supplied development references, not a verified training or
evaluation dataset. The MusicXML has not been checked here against the PDF.
The files remain local and are ignored by Git.

Generated images and reports belong under the producing experiment's `outputs/`,
not here. Music fonts come from the installed Verovio package; no separately downloaded
Petaluma bundle is retained in this repository.
