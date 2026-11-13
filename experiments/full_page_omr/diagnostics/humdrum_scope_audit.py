"""Isolated smoke probes for the selected Humdrum scope; no data files written.

This measures conversion/reimport and selected feature counts, not normalization,
visual fidelity, MusicXML export or recognition. Native faults stay in children.
"""
import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import version

from experiments.full_page_omr.representation.codec_fixtures import horn, piano, drums

FIXTURES = {'horn': horn, 'piano': piano, 'drums': drums}


def probe(name):
    # Conversion libraries have previously aborted on valid fixtures. Do not
    # allow a native fault to leave a core file containing a synthetic label.
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    import verovio
    source = FIXTURES[name]().source
    original = ET.fromstring(source)
    toolkit = verovio.toolkit()
    toolkit.setOptions(dict(inputFrom='musicxml-hum'))
    loaded = bool(toolkit.loadData(source))
    text = toolkit.getHumdrumBuffer() if loaded else ''
    if not loaded or not text:
        raise ValueError('MusicXML-to-Humdrum conversion produced no data')
    reader = verovio.toolkit()
    reader.setOptions(dict(inputFrom='humdrum'))
    if not reader.loadData(text):
        raise ValueError('Converted Humdrum did not reimport')
    mei = ET.fromstring(reader.getMEI())
    for node in mei.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    markings = [node.text for node in original.findall('.//words') if node.text]
    mei_text = ''.join(mei.itertext())
    return dict(
        fixture=name, verovio_version=version('verovio'), converted=True, reimported=True,
        humdrum_bytes=len(text.encode('utf-8')),
        initial_kern_spines=max((line.split('\t').count('**kern') for line in text.splitlines()), default=0),
        contains_dynamics_spine='**dynam' in text, contains_voice_split='*^' in text,
        text_layout_records=sum(line.startswith('!') and 'LO:TX' in line for line in text.splitlines()),
        source_words=len(markings), reimported_words_found=sum(mark in mei_text for mark in markings),
        source_note_events=sum(node.find('rest') is None for node in original.findall('.//note')),
        source_rest_events=sum(node.find('rest') is not None for node in original.findall('.//note')),
        source_pedal_markers=len(original.findall('.//pedal')),
        source_glissando_markers=len(original.findall('.//glissando')),
        mei_counts={tag:len(mei.findall('.//'+tag)) for tag in
                    ('note','rest','chord','dynam','dir','pedal','hairpin','slur','tie','tuplet','gliss')},
        acceptance='unverified; counts and substring checks are smoke evidence only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', choices=FIXTURES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe(args.probe)))
        return 0
    results = []
    for name in FIXTURES:
        try:
            child = subprocess.run(
                [sys.executable, '-m', __spec__.name, '--probe', name],
                capture_output=True, text=True, timeout=15)
            if child.returncode:
                results.append(dict(fixture=name, error='conversion process failed',
                                    returncode=child.returncode, diagnostics=child.stderr[-1000:]))
            else:
                results.append(json.loads(child.stdout))
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            results.append(dict(fixture=name, error=str(error)))
    print(json.dumps(dict(results=results), indent=2))
    # Success means the probes executed, not that the notation passed acceptance.
    return int(any('error' in result for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
