"""Warm native process reuse, replay, crashes, deadlines and shutdown."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image
import curriculum
import recipes
from preview_worker import PreviewWorker


class PreviewWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        (self.data/'doc').mkdir()
        Image.new('RGB', (100, 140), 'white').save(self.data/'doc/page-1.png')
        self.documents = [dict(id='doc', sha256='fixture', pages=[dict(number=1)])]
        self.scan = dict(stage='4', document_id='doc', page=1, settings=dict(recipe=[],seed=42))
        self.environment = patch.dict(os.environ,
            {'DYLD_FALLBACK_LIBRARY_PATH': '/opt/homebrew/lib'}
            if Path('/opt/homebrew/lib/libcairo.2.dylib').is_file() else {})
        self.environment.start()
        self.worker = PreviewWorker()

    def tearDown(self):
        self.worker.close()
        self.environment.stop()
        self.temp.cleanup()

    def fake(self, body):
        script = ('from pathlib import Path; import sys,time,os; '
                  'root=Path(sys.argv[1]); '
                  '(root/"ready.json").write_text("{}"); '
                  'sys.stdin.readline(); ' + body)
        return patch.object(self.worker, '_command', return_value=[sys.executable, '-c', script, str(self.worker.root)])

    def test_main_thread_cross_font_replay_same_process_and_isolated_equivalence(self):
        pid = self.worker.start()
        results = []
        events = []
        for font in ['Leipzig', 'Bravura', 'Petaluma']*2:
            request = dict(stage='1', example='passage', font=font, music_seed=7,
                           settings=dict(recipe=recipes.PRESETS['light-copy'], seed=42))
            result = self.worker.preview(self.data, request, [], progress=events.append)
            self.assertEqual(self.worker.pid, pid)
            results.append(result)
        for first, second in zip(results[:3], results[3:]):
            self.assertEqual(first['files'], second['files'])
            self.assertNotEqual(first['id'], second['id'])
        isolated = curriculum.preview_isolated(self.data, results[-1]['request'], [])
        self.assertEqual(results[-1]['files'], isolated['files'])
        with self.assertRaises(ValueError):
            self.worker.preview(self.data, dict(stage='unknown'), [])
        self.assertEqual(self.worker.pid, pid)
        self.assertEqual(self.worker.preview(self.data, results[-1]['request'], [])['files'], results[-1]['files'])
        self.assertEqual(events[-1]['fraction'], .99)
        self.assertFalse(any('Warming' in event['label'] for event in events))

    def test_fatal_exit_retires_process_and_next_job_restarts(self):
        with self.fake('os._exit(23)'):
            with self.assertRaisesRegex(RuntimeError, 'exited.*23'):
                self.worker.preview(self.data, self.scan, self.documents)
        self.assertIsNone(self.worker.pid)
        result = self.worker.preview(self.data, self.scan, self.documents)
        self.assertEqual(result['source']['kind'], 'real-scan')
        self.assertIsNotNone(self.worker.pid)

    def test_job_timeout_retires_process_and_next_job_restarts(self):
        self.worker.timeout = .12
        with self.fake('time.sleep(60)'):
            with self.assertRaisesRegex(TimeoutError, 'exceeded 0.12 seconds'):
                self.worker.preview(self.data, self.scan, self.documents)
        self.assertIsNone(self.worker.pid)
        self.worker.timeout = 10
        self.assertEqual(self.worker.preview(self.data, self.scan, self.documents)['source']['kind'], 'real-scan')

    def test_startup_timeout_and_close_during_active_job(self):
        self.worker.startup_timeout = .12
        command = [sys.executable, '-c', 'import time; time.sleep(60)']
        with patch.object(self.worker, '_command', return_value=command):
            with self.assertRaises(TimeoutError):
                self.worker.start()
        self.assertIsNone(self.worker.pid)
        self.worker.startup_timeout = 10
        with self.fake('(root/"started").write_text("1"); time.sleep(60)'), ThreadPoolExecutor(1) as executor:
            pending = executor.submit(self.worker.preview, self.data, self.scan, self.documents)
            deadline = time.monotonic()+3
            while not (self.worker.root/'started').is_file() and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertTrue((self.worker.root/'started').is_file())
            self.worker.close()
            with self.assertRaises(RuntimeError):
                pending.result(timeout=2)
        self.assertIsNone(self.worker.pid)
        self.assertFalse(self.worker.root.exists())


if __name__ == '__main__':
    unittest.main()
