"""Reproducible diagnostics for the legacy target path; no training or downloads.

Run from the repository root:
    .venv/bin/python -m experiments.full_page_omr.audit_target_format

Parser functions are compiled unchanged from their source ASTs, avoiding dataset,
GPU and ImageMagick initialization. These are probes of production function
bodies, not a replacement tokenizer. Inline fixtures are original synthetic
examples, not transcriptions of the user's scans. Results describe this installed
pipeline, not all possible Humdrum/MEI implementations.
"""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent


def load_parser(relative_path, function_name):
    path = ROOT / relative_path
    source = path.read_text()
    functions = [node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef)
                 and node.name in ("clean_kern", function_name)]
    scope = {"re": re}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), scope)
    return scope[function_name], hashlib.sha256(source.encode()).hexdigest()


def two_spines(body):
    return "**kern\t**kern\n" + body + "\n*-\t*-\n"


def parser_probes():
    parse, data_hash = load_parser("data.py", "parse_kern_file")
    generator_parse, generator_hash = load_parser("Generator/SynthGenerator.py", "parse_kern")
    cases = []

    def check(name, observed, interpretation):
        cases.append(dict(name=name, observed=observed, interpretation=interpretation))

    baseline = two_spines("*M4/4\t*M4/4\n=12\t=12\n1C\t1c")
    check("bar_numbers_collide", parse(baseline) == parse(baseline.replace("=12", "=99")),
          "True means different printed/internal bar numbers have identical targets.")
    for marker in ("*staff1", "*ped", "*Xped", "*cue", "*Xcue", "*tuplet", "*rscale:1/2"):
        with_marker = two_spines(marker + "\t*\n1C\t1c")
        check("removed_" + marker, parse(with_marker) == parse(two_spines("1C\t1c")),
              "True means this interpretation is erased.")
    mixed = two_spines("*ped\t*clefF4\n1C\t1c")
    check("unrelated_clef_on_removed_row", "*clefF4" in parse(mixed),
          "False means a pedal marker causes the other spine's clef to be erased too.")
    one = "**kern\n*M4/4\n=1\n1c\n*-\n"
    check("single_staff_meter_retained", "*M4/4" in parse(one),
          "False exposes the fixed four-field header skip on one spine.")
    three = "**kern\t**kern\t**kern\n1C\t1c\t1e\n*-\t*-\t*-\n"
    check("three_staff_header_fully_removed", "**kern" not in parse(three),
          "False means a third header field leaks into the nominally header-free target.")
    metadata = "!!!OTL:Audit title\n" + baseline
    check("metadata_moves_header_into_target", "**kern" in parse(metadata),
          "True means metadata changes what the positional header skip removes.")
    check("newline_changes_target", parse(baseline) != parse(baseline.rstrip("\n")),
          "True means trailing newline presence changes target tokens.")
    check("newline_free_final_terminator_retained", parse(baseline.rstrip("\n"))[-1] == "*-",
          "False means the final terminator was sliced off.")
    split = two_spines("*M4/4\t*M4/4\n*^\t*\n2C\t4c\t2e\n.\t4d\t.\n*v\t*v\t*\n2G\t2g")
    check("voice_split_join_and_null_retained", all(x in parse(split) for x in ("*^", "*v", ".")),
          "Token retention only, not a complete semantic polyphony round trip.")
    chord = two_spines("*M4/4\t*M4/4\n1C\t1c 1e 1g")
    dotted = two_spines("*M4/4\t*M4/4\n2..C\t2..c\n8G\t8g")
    check("chord_separator_retained", "<s>" in parse(chord), "Space/chord boundaries survive tokenization.")
    check("double_dot_retained", "2..c" in parse(dotted), "Basic duration spelling survives tokenization.")
    decoded = "**kern\t**kern\n" + "".join(parse(chord)).replace("<b>", "\n").replace("<t>", "\t").replace("<s>", " ")
    check("simple_chord_text_round_trip", decoded == chord,
          "Restricted two-spine text reconstruction, not MusicXML export or general fidelity.")
    check("generator_and_loader_agree_on_marker_free_case",
          generator_parse(chord).split() == parse(chord), "Restricted control case.")
    return dict(source_sha256={"data.py": data_hash, "Generator/SynthGenerator.py": generator_hash}, cases=cases)


def conversion_fixture():
    """Original two-staff micro-score with three independent voices and metadata."""
    return '''<score-partwise version="4.0">
<work><work-title>Target audit</work-title></work>
<identification><creator type="composer">Audit Composer</creator><rights>Audit rights</rights></identification>
<credit><credit-type>title</credit-type><credit-words>Target audit</credit-words></credit>
<part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
<part id="P1"><measure number="12"><attributes><divisions>4</divisions><key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves>
<clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>
<direction placement="above"><direction-type><rehearsal>A</rehearsal></direction-type><staff>1</staff></direction>
<direction placement="above"><direction-type><words>rit.</words></direction-type><staff>1</staff></direction>
<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>160</per-minute></metronome></direction-type><sound tempo="160"/></direction>
<direction><direction-type><dynamics><mf/></dynamics></direction-type><staff>1</staff></direction>
<direction><direction-type><wedge type="crescendo" number="1"/></direction-type><staff>1</staff></direction>
<direction><direction-type><pedal type="start"/></direction-type><staff>2</staff></direction>
<note><pitch><step>C</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff><notations><articulations><falloff/></articulations><slur type="start" number="1"/></notations></note>
<note><chord/><pitch><step>E</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff></note>
<note><pitch><step>D</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><type>half</type><staff>1</staff><notations><fermata/><slur type="stop" number="1"/></notations></note>
<backup><duration>16</duration></backup>
<note><pitch><step>G</step><octave>4</octave></pitch><duration>16</duration><voice>2</voice><type>whole</type><staff>1</staff></note>
<backup><duration>16</duration></backup>
<note><pitch><step>C</step><octave>3</octave></pitch><duration>16</duration><voice>3</voice><type>whole</type><staff>2</staff></note>
<direction><direction-type><wedge type="stop" number="1"/></direction-type><staff>1</staff></direction>
<direction><direction-type><pedal type="stop"/></direction-type><staff>2</staff></direction>
<barline location="right"><bar-style>light-light</bar-style></barline>
</measure></part></score-partwise>'''


def percussion_fixture():
    return '''<score-partwise version="4.0"><part-list><score-part id="P1">
<part-name>Drums</part-name><score-instrument id="ride"><instrument-name>Ride cymbal</instrument-name></score-instrument>
<score-instrument id="kick"><instrument-name>Bass drum</instrument-name></score-instrument></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time>
<clef><sign>percussion</sign></clef></attributes>
<direction><direction-type><words>BRUSHES</words></direction-type></direction>
<note><unpitched><display-step>G</display-step><display-octave>5</display-octave></unpitched><duration>16</duration>
<instrument id="ride"/><voice>1</voice><type>whole</type><notehead>x</notehead></note><backup><duration>16</duration></backup>
<note><unpitched><display-step>F</display-step><display-octave>4</display-octave></unpitched><duration>16</duration>
<instrument id="kick"/><voice>2</voice><type>whole</type><notehead>normal</notehead></note>
</measure></part></score-partwise>'''


def humdrum_fixture():
    return two_spines("*M4/4\t*M4/4\n*clefF4\t*clefG2\n=1\t=1\n*\t*^\n2C\t4c 4e\t2g\n.\t4d\t.\n*\t*v\t*v\n2G\t2c")


def conversion_probe(route, fixture="piano"):
    import verovio
    toolkit = verovio.toolkit()
    toolkit.setOptions({"inputFrom": route})
    # Flush stage markers to stderr so native failures can be localized.
    print("loading " + route, file=sys.stderr, flush=True)
    source = {"piano": conversion_fixture, "drums": percussion_fixture, "humdrum": humdrum_fixture}[fixture]()
    if not toolkit.loadData(source):
        raise ValueError("fixture rejected")
    print("loaded " + route, file=sys.stderr, flush=True)
    mei = toolkit.getMEI()
    root = ET.fromstring(mei)
    q = lambda name: "{http://www.music-encoding.org/ns/mei}" + name
    result = dict(version=toolkit.getVersion(), mei_elements=dict(Counter(n.tag.split('}')[-1] for n in root.iter())),
                  staff_layers=[dict(staff=s.get("n"), layers=[l.get("n") for l in s.findall(q("layer"))])
                                for s in root.iter(q("staff"))],
                  texts={name: ["".join(n.itertext()).strip() for n in root.iter(q(name))]
                         for name in ("title", "composer", "persName", "availability", "reh", "dir", "dynam")},
                  articulations=[{k: v for k, v in n.attrib.items() if not k.endswith('}id')}
                                 for n in root.iter(q("artic"))],
                  notes=[{k: v for k, v in n.attrib.items() if not k.endswith('}id')}
                         for n in root.iter(q("note"))],
                  instrument_metadata=[dict(tag=n.tag.split('}')[-1], attributes=n.attrib, text=n.text)
                                       for n in root.iter() if "instr" in n.tag.lower()])
    if fixture == "humdrum":
        parse, _ = load_parser("data.py", "parse_kern_file")
        decoded = "**kern\t**kern\n" + "".join(parse(source)).replace("<b>", "\n").replace("<t>", "\t").replace("<s>", " ")
        other = verovio.toolkit()
        other.setOptions({"inputFrom": "humdrum"})
        if not other.loadData(decoded):
            raise ValueError("decoded Humdrum rejected")
        def fingerprint(xml):
            tree = ET.fromstring(xml)
            # Exclude generated IDs and bar labels; bar-number loss is tested separately.
            return [(node.tag.split('}')[-1], {k: v for k, v in node.attrib.items()
                     if not k.endswith('}id') and k not in ("startid", "endid")})
                    for staff in tree.iter(q("staff")) for node in staff.iter()]
        result["staff_event_fingerprint_round_trip"] = fingerprint(mei) == fingerprint(other.getMEI())
    if route == "musicxml-hum":
        humdrum = toolkit.getHumdrumBuffer()
        result["humdrum"] = humdrum
    return result


def run_conversion(route, fixture="piano"):
    try:
        process = subprocess.run([sys.executable, "-m", "experiments.full_page_omr.audit_target_format", "--probe", route, "--fixture", fixture],
                                 cwd=ROOT.parents[1], text=True, capture_output=True, timeout=30)
    except subprocess.TimeoutExpired:
        return dict(route=route, fixture=fixture, error="30-second timeout")
    result = dict(route=route, fixture=fixture, returncode=process.returncode, diagnostics=process.stderr)
    if process.returncode == 0:
        result["result"] = json.loads(process.stdout)
    else:
        result["error"] = process.stdout
    return result


def vocabulary_probes():
    import numpy as np
    result = []
    for path in sorted((ROOT / "vocab").glob("*w2i.npy")):
        vocab = np.load(path, allow_pickle=True).item()  # Repository-owned dictionaries only.
        result.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=len(vocab),
                           structural={x: x in vocab for x in ("*^", "*v", "*ped", "*cue", "*staff1", "*staff2")},
                           arbitrary_text_example_covered="BRUSHES" in vocab))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New JSON report; refuses existing files")
    parser.add_argument("--probe", choices=("musicxml", "musicxml-hum", "humdrum"), help=argparse.SUPPRESS)
    parser.add_argument("--fixture", choices=("piano", "drums", "humdrum"), default="piano", help=argparse.SUPPRESS)
    parser.add_argument("--include-humdrum-converter", action="store_true",
                        help="Probe native MusicXML/Humdrum converter in an isolated subprocess")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(conversion_probe(args.probe, args.fixture)))
        return
    if args.output and args.output.exists():
        parser.error("output already exists")
    routes = ["musicxml"] + (["musicxml-hum"] if args.include_humdrum_converter else [])
    result = dict(schema_version=1, parser=parser_probes(), vocabularies=vocabulary_probes(),
                  conversion=[run_conversion(route) for route in routes]
                  + [run_conversion("musicxml", "drums"), run_conversion("humdrum", "humdrum")])
    content = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(content)
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
