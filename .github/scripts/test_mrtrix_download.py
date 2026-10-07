import ast
import contextlib
import email.utils
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import urllib.error
from unittest.mock import patch


NOTEBOOK_DIRECTORY = Path(__file__).resolve().parents[2] / 'books/examples/diffusion_imaging'
VALID_IMAGE = b'complete image payload'
SHA256 = hashlib.sha256(VALID_IMAGE).hexdigest()
REMOTE = 'preprocessed/image with spaces.nii.gz'


def load_helper(number):
    notebook = json.loads((NOTEBOOK_DIRECTORY / f'MRtrix_{number}.ipynb').read_text())
    source = next(''.join(c['source']) for c in notebook['cells']
                  if 'def fetch_if_missing' in ''.join(c['source']))
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))]
    namespace = {'os': os}
    exec(compile(tree, f'MRtrix_{number}.ipynb', 'exec'), namespace)
    return namespace['fetch_if_missing']


def expected_url(number):
    revision = load_helper(number).__globals__['REVISION']
    return ('https://huggingface.co/datasets/neurodeskorg/mrtrix-tutorial-data'
            f'/resolve/{revision}/{REMOTE}')


def http_error(code, retry_after=None):
    headers = {'Retry-After': retry_after} if retry_after else {}
    return urllib.error.HTTPError(REMOTE, code, 'error', headers, None)


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.contexts = contextlib.ExitStack()
        self.addCleanup(self.contexts.close)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.local = self.directory / 'image with spaces.nii.gz'
        self.requests = []
        self.outcomes = []
        self.contexts.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.sleep = self.contexts.enter_context(patch('time.sleep'))
        self.contexts.enter_context(patch('urllib.request.urlopen', side_effect=self.urlopen))

    def urlopen(self, url, timeout=None):
        self.assertEqual(url, self.url)
        self.assertGreater(timeout or 0, 0)
        self.requests.append(url)
        result = self.outcomes.pop(0) if self.outcomes else VALID_IMAGE
        if isinstance(result, Exception):
            raise result
        return io.BytesIO(result)

    def stray_files(self):
        return [p for p in self.directory.iterdir()
                if p != self.local and not p.name.endswith('.invalid')]

    def each_helper(self):
        for number in (2, 3):
            self.requests.clear()
            self.sleep.reset_mock()
            if self.local.exists():
                self.local.unlink()
            self.url = expected_url(number)
            yield number, load_helper(number)

    def test_valid_cache_is_reused(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.local.write_bytes(VALID_IMAGE)
                fetch(REMOTE, SHA256, str(self.local))
                self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                self.assertEqual(self.requests, [])

    def test_invalid_cache_is_preserved_and_replaced(self):
        for number, fetch in self.each_helper():
            for corrupt in (b'HTTP 429', b'truncated image'):
                with self.subTest(notebook=number, corrupt=corrupt):
                    previous = set(self.directory.glob('*.invalid'))
                    self.local.write_bytes(corrupt)
                    fetch(REMOTE, SHA256, str(self.local))
                    self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                    saved = set(self.directory.glob('*.invalid')) - previous
                    self.assertEqual(len(saved), 1)
                    self.assertEqual(saved.pop().read_bytes(), corrupt)

    def test_transient_failure_retries_then_promotes_valid_image(self):
        for number, fetch in self.each_helper():
            for failure in (http_error(429), http_error(503),
                            urllib.error.URLError('reset'), TimeoutError(),
                            b'truncated image'):
                with self.subTest(notebook=number, failure=failure):
                    self.requests.clear()
                    self.sleep.reset_mock()
                    if self.local.exists():
                        self.local.unlink()
                    self.outcomes = [failure, VALID_IMAGE]
                    fetch(REMOTE, SHA256, str(self.local))
                    self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                    self.assertEqual(len(self.requests), 2)
                    self.assertEqual(self.sleep.call_count, 1)
                    self.assertEqual(self.stray_files(), [])

    def test_retry_after_extends_backoff(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.outcomes = [http_error(429, retry_after='900'), VALID_IMAGE]
                fetch(REMOTE, SHA256, str(self.local))
                self.sleep.assert_called_once_with(900)

    def test_retry_after_accepts_http_date(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.sleep.reset_mock()
                when = email.utils.formatdate(time.time() + 600, usegmt=True)
                self.outcomes = [http_error(429, retry_after=when), VALID_IMAGE]
                fetch(REMOTE, SHA256, str(self.local))
                [delay] = [call.args[0] for call in self.sleep.call_args_list]
                self.assertTrue(550 <= delay <= 600, delay)

    def test_local_io_error_fails_without_retry(self):
        for number, fetch in self.each_helper():
            for failure in (PermissionError(errno.EACCES, 'denied'),
                            OSError(errno.ENOSPC, 'No space left on device')):
                with self.subTest(notebook=number, failure=failure):
                    self.requests.clear()
                    self.sleep.reset_mock()
                    with patch('shutil.copyfileobj', side_effect=failure):
                        with self.assertRaises(OSError) as error:
                            fetch(REMOTE, SHA256, str(self.local))
                    self.assertIs(error.exception, failure)
                    self.assertEqual(len(self.requests), 1)
                    self.sleep.assert_not_called()
                    self.assertFalse(self.local.exists())
                    self.assertEqual(self.stray_files(), [])

    def test_exhaustion_leaves_no_cache_and_preserves_cause(self):
        for number, fetch in self.each_helper():
            for outcome in (b'HTTP 429', http_error(429), urllib.error.URLError('reset')):
                with self.subTest(notebook=number, outcome=outcome):
                    self.requests.clear()
                    self.sleep.reset_mock()
                    self.outcomes = [outcome] * 20
                    with self.assertRaises(RuntimeError) as error:
                        fetch(REMOTE, SHA256, str(self.local))
                    self.assertIn(self.url, str(error.exception))
                    self.assertIn(str(self.local), str(error.exception))
                    self.assertIsNotNone(error.exception.__cause__)
                    self.assertFalse(self.local.exists())
                    self.assertGreater(len(self.requests), 3)
                    self.assertLessEqual(len(self.requests), 10)
                    self.assertEqual(self.sleep.call_count, len(self.requests) - 1)
                    # OSF rate limits outlast a short backoff; keep waiting for minutes.
                    total = sum(call.args[0] for call in self.sleep.call_args_list)
                    self.assertGreaterEqual(total, 300)
                    self.assertEqual(self.stray_files(), [])

    def test_client_error_fails_without_retry(self):
        for number, fetch in self.each_helper():
            for code in (403, 404):
                with self.subTest(notebook=number, code=code):
                    self.requests.clear()
                    self.outcomes = [http_error(code)]
                    with self.assertRaises(urllib.error.HTTPError):
                        fetch(REMOTE, SHA256, str(self.local))
                    self.assertEqual(len(self.requests), 1)
                    self.sleep.assert_not_called()
                    self.assertFalse(self.local.exists())
                    self.assertEqual(self.stray_files(), [])


class PinnedFilesTest(unittest.TestCase):
    def test_every_download_pins_a_mirror_path_and_sha256(self):
        for number in (2, 3):
            notebook = json.loads((NOTEBOOK_DIRECTORY / f'MRtrix_{number}.ipynb').read_text())
            source = next(''.join(c['source']) for c in notebook['cells']
                          if 'def fetch_if_missing' in ''.join(c['source']))
            calls = [node for node in ast.walk(ast.parse(source))
                     if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'fetch_if_missing']
            with self.subTest(notebook=number):
                self.assertRegex(load_helper(number).__globals__['REVISION'], r'^[0-9a-f]{40}$')
                self.assertEqual(len(calls), 5)
                for call in calls:
                    remote, sha256, local = (arg.value for arg in call.args)
                    self.assertRegex(remote, r'^(preprocessed|fod)/[\w.-]+$')
                    self.assertEqual(Path(remote).name, Path(local).name)
                    self.assertRegex(sha256, r'^[0-9a-f]{64}$')
                    self.assertTrue(local.startswith('MRtrix_'))


if __name__ == '__main__':
    unittest.main()
