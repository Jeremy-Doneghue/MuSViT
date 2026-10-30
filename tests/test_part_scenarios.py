from collections import Counter
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.full_page_omr.generate_parts import generate, render_musicxml, to_mei
from experiments.full_page_omr.musicxml_score import to_musicxml
from experiments.full_page_omr.scenarios import (
    FEATURES, HOLDOUTS, ScenarioSpec, expand_features, make_scenario, observe_features, plan_dataset,
)


class ScenarioTests(unittest.TestCase):
    def test_mixture_and_split_reproducibility(self):
        plan = plan_dataset(20, seed=42)
        self.assertEqual(Counter(spec.profile for _, spec in plan),
                         {"focused": 10, "combined": 7, "complete": 3})
        self.assertEqual(plan, plan_dataset(20, seed=42))
        self.assertEqual(sum(not spec.features for _, spec in plan), 2)
        train_seeds = {seed for seed, _ in plan}
        self.assertFalse(train_seeds & {seed for seed, _ in plan_dataset(20, seed=42, split="test")})
        for _, spec in plan:
            self.assertFalse(any(pair <= set(spec.features) for pair in HOLDOUTS.values()))

    def test_each_feature_can_be_requested_independently(self):
        baseline = {"beams", "duration_rests"}
        for feature in sorted(FEATURES):
            with self.subTest(feature=feature):
                spec = ScenarioSpec("focused", (feature,), 16)
                part = make_scenario(7, spec)
                actual = observe_features(to_musicxml(part))
                requested = expand_features(spec.features)
                self.assertFalse(requested - actual.keys())
                allowed = requested | baseline | ({"repeat"} if feature == "endings" else set())
                self.assertFalse((actual.keys() & FEATURES) - allowed)
                to_mei(part)

    def test_diverse_recipes_keep_visible_coverage_and_convert(self):
        for split in ("train", "validation", "test"):
            for dataset_seed in range(2):
                for seed, spec in plan_dataset(20, dataset_seed, split=split):
                    with self.subTest(split=split, seed=seed):
                        part = make_scenario(seed, spec)
                        actual = observe_features(to_musicxml(part))
                        self.assertFalse(expand_features(spec.features) - actual.keys())
                        if split == "train":
                            self.assertFalse(any(pair <= actual.keys() for pair in HOLDOUTS.values()))
                        elif spec.profile in ("combined", "complete"):
                            self.assertTrue(HOLDOUTS[split] <= actual.keys())
                        to_mei(part)

    def test_feature_locations_vary(self):
        spec = ScenarioSpec("combined", ("key_changes", "multibar_rests", "improvisation"), 20, 2)
        locations = {feature: set() for feature in ("key_changes", "multibar_rests", "improvisation_slashes")}
        for seed in range(12):
            part = make_scenario(seed, spec)
            observed = observe_features(to_musicxml(part))
            for feature in locations:
                locations[feature].add(tuple(observed[feature]))
        self.assertTrue(all(len(values) >= 4 for values in locations.values()))

    def test_length_and_page_count_are_independent(self):
        parts = [make_scenario(11, ScenarioSpec("focused", ("repeat",), 8, pages)) for pages in (1, 2)]
        self.assertEqual(parts[0].measures, parts[1].measures)
        self.assertEqual(parts[0].playback, parts[1].playback)
        with tempfile.TemporaryDirectory() as directory:
            for pages, part in enumerate(parts, 1):
                layout = render_musicxml(to_musicxml(part), Path(directory) / str(pages))
                self.assertEqual(len(layout["pages"]), pages)
                if pages == 2:
                    self.assertNotEqual(layout["measure_pages"][part.navigation["start"]],
                                        layout["measure_pages"][part.navigation["end"]])

    def test_signature_change_at_multibar_rest_survives(self):
        spec = ScenarioSpec("combined", ("key_changes", "multibar_rests"), 12, 2)
        part = make_scenario(12291573813637836556, spec)
        self.assertEqual(part.multirests[0][0], "m3")
        self.assertNotEqual(part.measures[1].key, part.measures[2].key)
        to_mei(part)  # Previously Verovio silently dropped this change.

    def test_exported_manifest_reports_actual_features_and_cost(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            manifest = generate(directory, count=20, seed=0)
            self.assertEqual(manifest["profile_counts"], {"focused": 10, "combined": 7, "complete": 3})
            self.assertEqual(manifest, json.loads((Path(directory) / "manifest.json").read_text()))
            for record in manifest["examples"]:
                source = (Path(directory) / record["example"] / "source.musicxml").read_text()
                observed = observe_features(source)
                self.assertEqual(record["actual_features"], sorted(observed))
                self.assertFalse(set(record["requested_features"]) - observed.keys())
                if record["scenario"] != "plain" and record["pages"] > 1:
                    self.assertTrue(record["cross_page_navigation"])
                for feature, positions in record["feature_locations"].items():
                    self.assertEqual([p["measure"] for p in positions], observed[feature])
                root = ET.fromstring(source)
                self.assertEqual(record["measure_count"], len(root.findall("part/measure")))
            self.assertEqual(sum(manifest["note_events_by_profile"].values()),
                             sum(r["note_events"] for r in manifest["examples"]))
            with self.assertRaises(FileExistsError):
                generate(directory, count=20)

    def test_invalid_requests_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown features"):
            expand_features(["not-a-feature"])
        with self.assertRaisesRegex(ValueError, "at most one"):
            expand_features(["repeat", "ds_coda"])
        with self.assertRaisesRegex(ValueError, "reserved"):
            plan_dataset(1, profile="combined", features=["meter_changes", "two_bar_simile"])
        with self.assertRaisesRegex(ValueError, "single --profile"):
            plan_dataset(1, features=["accent"])
        with self.assertRaisesRegex(ValueError, "at least"):
            make_scenario(0, ScenarioSpec("focused", ("two_bar_simile", "multibar_rests"), 4))


if __name__ == "__main__":
    unittest.main()
