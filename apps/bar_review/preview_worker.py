"""One warm, serial preview subprocess for a desktop session.

Native renderer code stays on the child's main thread. A crash/timeout retires
that process; the next request starts a fresh one. The GUI thread never waits.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import uuid


class PreviewWorker:
    def __init__(self, *, timeout=120, startup_timeout=120):
        self.timeout = timeout
        self.startup_timeout = startup_timeout
        self._temporary = tempfile.TemporaryDirectory(prefix='musvit-warm-preview-')
        self.root = Path(self._temporary.name)
        self._process = None
        self._log = None
        self._serial = threading.Lock()
        self._lifecycle = threading.Lock()
        self._closed = threading.Event()

    @property
    def pid(self):
        process = self._process
        return process.pid if process and process.poll() is None else None

    def _command(self):
        return [sys.executable, str(Path(__file__).with_name('curriculum.py')),
                '--persistent-worker', str(self.root)]

    def _wait(self, path, process, timeout, progress=None, progress_path=None):
        deadline = time.monotonic() + timeout
        previous = None
        while True:
            if self._closed.is_set():
                raise RuntimeError('Preview worker closed.')
            if path.is_file():
                return json.loads(path.read_text())
            code = process.poll()
            if code is not None:
                detail = (self.root/'worker.log').read_text(errors='replace')[-4000:]
                raise RuntimeError(f'Preview worker exited ({code}). It will restart on the next preview.\n{detail}')
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Preview worker exceeded {timeout:g} seconds. It will restart on the next preview.')
            if progress and progress_path:
                try:
                    value = json.loads(progress_path.read_text())
                except (OSError, ValueError):
                    value = None
                if value is not None and value != previous:
                    progress(value)
                    previous = value
            self._closed.wait(.04)

    def _stop(self):
        with self._lifecycle:
            process, self._process = self._process, None
            if process:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if process.stdin:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
            if self._log:
                self._log.close()
                self._log = None

    def _ensure_ready(self, progress):
        if self._closed.is_set():
            raise RuntimeError('Preview worker closed.')
        process = self._process
        if process and process.poll() is None and (self.root/'ready.json').is_file():
            return process
        self._stop()
        with self._lifecycle:
            if self._closed.is_set():
                raise RuntimeError('Preview worker closed.')
            (self.root/'ready.json').unlink(missing_ok=True)
            (self.root/'startup.progress.json').unlink(missing_ok=True)
            self._log = (self.root/'worker.log').open('ab')
            self._process = process = subprocess.Popen(self._command(), stdin=subprocess.PIPE,
                stdout=self._log, stderr=subprocess.STDOUT, text=True, bufsize=1,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'})
        if progress:
            progress(dict(label='Warming preview worker (once per session)', fraction=.02))
        try:
            self._wait(self.root/'ready.json', process, self.startup_timeout, progress,
                       self.root/'startup.progress.json')
        except Exception:
            self._stop()
            raise
        return process

    def start(self, *, progress=None):
        """Preload dependencies asynchronously when called through the GUI executor."""
        with self._serial:
            process = self._ensure_ready(progress)
            if progress:
                progress(dict(label='Preview worker ready', fraction=1))
            return process.pid

    def preview(self, data, payload, documents, *, progress=None, source_preview=None):
        with self._serial:
            process = self._ensure_ready(progress)
            job_id = uuid.uuid4().hex
            result_path = self.root/f'{job_id}.result.json'
            progress_path = self.root/f'{job_id}.progress.json'
            request = dict(id=job_id, data=str(Path(data).resolve()), payload=payload,
                           documents=documents, source_preview=source_preview)
            try:
                if progress:
                    progress(dict(label='Submitting preview to warm worker', fraction=.04))
                process.stdin.write(json.dumps(request)+'\n')
                process.stdin.flush()
                result = self._wait(result_path, process, self.timeout, progress, progress_path)
            except TimeoutError:
                self._stop()
                raise
            except OSError as error:
                self._stop()
                raise RuntimeError('Preview worker connection lost. It will restart on the next preview.') from error
            except Exception:
                self._stop()
                raise
            finally:
                result_path.unlink(missing_ok=True)
                progress_path.unlink(missing_ok=True)
            if not result['ok']:
                if result['type'] == 'ValueError':
                    raise ValueError(result['error'])
                self._stop()
                raise RuntimeError(result['error']+'\nThe worker will restart on the next preview.')
            if progress:
                progress(dict(label='Preview files ready', fraction=.99))
            return result['manifest']

    def close(self):
        """Stop idle or active rendering promptly, without waiting for a job lock."""
        self._closed.set()
        self._stop()
        self._temporary.cleanup()
