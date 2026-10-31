"""Re-engrave actual saved pilot predictions and compare with the input pages."""

import argparse
from importlib.util import find_spec
import json
from pathlib import Path

from PIL import Image, ImageChops


def review(dataset, run):
    import verovio
    from cairosvg import svg2png
    from .font_resources import outline_text

    dataset, run = Path(dataset), Path(run)
    result = json.loads((run / "result.json").read_text())
    records = json.loads((dataset / "manifest.json").read_text())["records"][:result["final"]["count"]]
    predictions = run / f"eval_{result['final']['step']:05d}"
    output = run / "reengraved"
    output.mkdir(exist_ok=False)
    font = Path(find_spec("matplotlib").origin).parent / "mpl-data/fonts/ttf/DejaVuSerif.ttf"
    comparisons = []
    for record in records:
        source = predictions / f"{record['name']}.musicxml"
        if not source.exists():
            comparisons.append(dict(name=record["name"], valid=False, pixels_equal=False))
            continue
        xml = source.read_text()
        toolkit = verovio.toolkit()
        toolkit.setOptions({"inputFrom": "musicxml", "breaks": "encoded" if "<print" in xml else "auto",
                            "pageWidth": 2100, "pageHeight": 2970, "scale": 40,
                            "header": "none", "footer": "none"})
        if not toolkit.loadData(xml) or toolkit.getPageCount() != 1:
            raise ValueError("predicted score is not a renderable single page")
        svg = toolkit.renderToSVG(1).replace('overflow="inherit"', 'overflow="visible"')
        svg, _ = outline_text(svg, font, font, output / "text_fonts", "Leipzig")
        (output / f"{record['name']}.svg").write_text(svg)
        png = output / f"{record['name']}.png"
        svg2png(bytestring=svg.encode(), write_to=str(png), output_width=1400, background_color="white")
        with Image.open(dataset / record["image"]) as expected, Image.open(png) as actual:
            equal = expected.size == actual.size and ImageChops.difference(expected.convert("RGB"), actual.convert("RGB")).getbbox() is None
        comparisons.append(dict(name=record["name"], valid=True, pixels_equal=equal))
    report = dict(prediction_step=result["final"]["step"], count=len(comparisons),
                  exact_renders=sum(c["pixels_equal"] for c in comparisons), examples=comparisons,
                  renderer=verovio.toolkit().getVersion())
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    review(args.dataset, args.run)
