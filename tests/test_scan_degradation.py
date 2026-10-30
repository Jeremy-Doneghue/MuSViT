import json
import random
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from numba import config as numba_config

from experiments.scan_degradation.generate import (
    LIBRARY_SCAN, PROFILES, bad_photocopy, export_preview, library_scan,
)


class ScanDegradationTests(unittest.TestCase):
    def test_library_scan_expands_canvas_without_mutating_parameters(self):
        source = np.full((480, 360), 255, dtype=np.uint8)
        source[80:400:8, 40:320] = 0
        original = source.copy()
        parameters = deepcopy(LIBRARY_SCAN)
        python_state, numpy_state = random.getstate(), np.random.get_state()
        jit_disabled = numba_config.DISABLE_JIT
        first = library_scan(source, parameters, 45)
        repeated = library_scan(source, parameters, 45)
        np.testing.assert_array_equal(first, repeated)
        np.testing.assert_array_equal(source, original)
        self.assertGreater(first.shape[0], source.shape[0])
        self.assertGreater(first.shape[1], source.shape[1])
        self.assertEqual(first.dtype, np.uint8)
        self.assertEqual(parameters, LIBRARY_SCAN)
        self.assertEqual(random.getstate(), python_state)
        np.testing.assert_array_equal(np.random.get_state()[1], numpy_state[1])
        self.assertEqual(numba_config.DISABLE_JIT, jit_disabled)

    def test_fixed_seed_preserves_preview_without_mutating_source_or_random_state(self):
        source = np.full((160, 240), 255, dtype=np.uint8)
        source[40:100, 20:220:4] = 0
        original = source.copy()
        python_state, numpy_state = random.getstate(), np.random.get_state()
        jit_disabled = numba_config.DISABLE_JIT
        for profile in PROFILES.values():
            first = bad_photocopy(source, profile, 42)
            repeated = bad_photocopy(source, profile, 42)
            different = bad_photocopy(source, profile, 43)
            np.testing.assert_array_equal(first, repeated)
            self.assertFalse(np.array_equal(first, different))
            self.assertEqual(first.shape, source.shape)
            self.assertEqual(first.dtype, np.uint8)
        np.testing.assert_array_equal(source, original)
        self.assertEqual(random.getstate(), python_state)
        current_numpy = np.random.get_state()
        np.testing.assert_array_equal(current_numpy[1], numpy_state[1])
        self.assertEqual(current_numpy[2:], numpy_state[2:])
        self.assertEqual(numba_config.DISABLE_JIT, jit_disabled)

    def test_export_saves_inspected_arrays_and_refuses_overwrite(self):
        source = np.full((160, 240), 255, dtype=np.uint8)
        variant = bad_photocopy(source, PROFILES['light-copy'], 42)
        manifest = {'backend': 'augraphy.BadPhotoCopy',
                    'variants': {'light-copy': {'seed': 42, 'parameters': PROFILES['light-copy']}}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run'
            export_preview(source, {'light-copy': variant}, manifest, output)
            with Image.open(output / 'light-copy.png') as image:
                np.testing.assert_array_equal(np.array(image), variant)
            with Image.open(output / 'clean.png') as image:
                np.testing.assert_array_equal(np.array(image), source)
            self.assertEqual(json.loads((output / 'manifest.json').read_text()), json.loads(json.dumps(manifest)))
            self.assertTrue((output / 'comparison.png').is_file())
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError):
                export_preview(source, {'light-copy': source}, {}, output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
