import ast
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


NOTEBOOK_DIRECTORY = Path(__file__).resolve().parents[2] / 'books/examples/diffusion_imaging'
VALID_IMAGE = b'complete image payload'


def load_helper(number):
    notebook = json.loads((NOTEBOOK_DIRECTORY / f'MRtrix_{number}.ipynb').read_text())
    source = next(''.join(c['source']) for c in notebook['cells']
                  if 'def fetch_if_missing' in ''.join(c['source']))
    tree = ast.parse(source)
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    namespace = {'os': os, 'np': np}
    exec(compile(tree, f'MRtrix_{number}.ipynb', 'exec'), namespace)
    return namespace['fetch_if_missing']


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.contexts = contextlib.ExitStack()
        self.addCleanup(self.contexts.close)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name) / 'image with spaces.nii.gz'
        self.remote = 'preprocessed/image with spaces.nii.gz'
        self.downloads = []
        self.outcomes = []
        self.contexts.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.sleep = self.contexts.enter_context(patch('time.sleep'))
        self.contexts.enter_context(patch('subprocess.run', side_effect=self.run_command))
        self.contexts.enter_context(patch('os.system', side_effect=self.run_legacy))

    def run_legacy(self, command):
        self.local.write_bytes(b'HTTP 429')
        self.downloads.append(self.local)
        return 256

    def run_command(self, args, **kwargs):
        self.assertIsInstance(args, list)
        self.assertTrue(kwargs.get('check'))
        self.assertGreater(kwargs.get('timeout', 0), 0)
        if args[0] == 'osf':
            self.assertEqual(args[:5], ['osf', '-p', 'y2dq4', 'fetch', self.remote])
            target = Path(args[5])
            self.assertEqual(target.name, self.local.name)
            self.assertFalse(target.exists())
            self.assertFalse(self.local.exists())
            self.downloads.append(target)
            result = self.outcomes.pop(0) if self.outcomes else VALID_IMAGE
            if isinstance(result, Exception):
                target.write_bytes(b'partial')
                raise result
            target.write_bytes(result)
        elif args[0] == 'mrstats':
            self.assertIn('count', args)
            image = Path(args[1])
            if image.read_bytes() != VALID_IMAGE:
                raise subprocess.CalledProcessError(1, args)
        else:
            self.fail(f'Unexpected command: {args}')
        return subprocess.CompletedProcess(args, 0)

    def each_helper(self):
        for number in (2, 3):
            self.downloads.clear()
            self.sleep.reset_mock()
            if self.local.exists():
                self.local.unlink()
            yield number, load_helper(number)

    def test_valid_cache_is_reused(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.local.write_bytes(VALID_IMAGE)
                fetch(self.remote, str(self.local))
                self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                self.assertEqual(self.downloads, [])

    def test_invalid_cache_is_preserved_and_replaced(self):
        for number, fetch in self.each_helper():
            for corrupt in (b'HTTP 429', b'truncated image'):
                with self.subTest(notebook=number, corrupt=corrupt):
                    previous = set(self.local.parent.glob('*.invalid*'))
                    self.local.write_bytes(corrupt)
                    fetch(self.remote, str(self.local))
                    self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                    saved = set(self.local.parent.glob('*.invalid*')) - previous
                    self.assertEqual(len(saved), 1)
                    self.assertEqual(saved.pop().read_bytes(), corrupt)

    def test_partial_failure_retries_then_promotes_valid_image(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.outcomes = [subprocess.CalledProcessError(1, 'osf'), VALID_IMAGE]
                fetch(self.remote, str(self.local))
                self.assertEqual(self.local.read_bytes(), VALID_IMAGE)
                self.assertEqual(len(self.downloads), 2)
                self.assertNotEqual(*self.downloads)
                self.assertTrue(all(not p.exists() for p in self.downloads))
                self.assertEqual(self.sleep.call_count, 1)

    def test_exhaustion_leaves_no_cache_and_preserves_cause(self):
        for number, fetch in self.each_helper():
            for outcome in (b'HTTP 429', b'truncated image',
                            subprocess.CalledProcessError(1, 'osf'),
                            subprocess.TimeoutExpired('osf', 600)):
                with self.subTest(notebook=number, outcome=outcome):
                    self.downloads.clear()
                    self.sleep.reset_mock()
                    self.outcomes = [outcome] * 10
                    with self.assertRaises(RuntimeError) as error:
                        fetch(self.remote, str(self.local))
                    self.assertIn(self.remote, str(error.exception))
                    self.assertIn(str(self.local), str(error.exception))
                    self.assertIsNotNone(error.exception.__cause__)
                    self.assertFalse(self.local.exists())
                    self.assertGreater(len(self.downloads), 1)
                    self.assertLessEqual(len(self.downloads), 5)
                    self.assertEqual(len(set(self.downloads)), len(self.downloads))
                    self.assertTrue(all(not p.exists() for p in self.downloads))
                    self.assertEqual(self.sleep.call_count, len(self.downloads) - 1)

    def test_missing_executable_fails_without_retry(self):
        for number, fetch in self.each_helper():
            with self.subTest(notebook=number):
                self.outcomes = [FileNotFoundError('osf')]
                with self.assertRaises(FileNotFoundError):
                    fetch(self.remote, str(self.local))
                self.assertEqual(len(self.downloads), 1)
                self.sleep.assert_not_called()
                self.assertFalse(self.local.exists())

    def test_gradient_validation(self):
        fetch = load_helper(2)
        for suffix, valid, invalid in (
            ('.bval', b'0 1000\n', [b'HTTP 429', b'-1 1000\n', b'0 nan\n', b'0\n1000\n']),
            ('.bvec', b'0 1\n0 0\n0 0\n', [b'HTTP 429', b'0 1\n0 0\n',
                                                  b'0 nan\n0 0\n0 0\n', b'0\n0\n0\n']),
        ):
            self.local = Path(self.temp.name) / ('diffusion' + suffix)
            self.remote = 'preprocessed/' + self.local.name
            self.outcomes = [valid]
            fetch(self.remote, str(self.local))
            self.assertEqual(self.local.read_bytes(), valid)
            downloads = len(self.downloads)
            fetch(self.remote, str(self.local))
            self.assertEqual(len(self.downloads), downloads)
            for corrupt in invalid:
                with self.subTest(suffix=suffix, corrupt=corrupt):
                    self.local.write_bytes(corrupt)
                    self.outcomes = [valid]
                    fetch(self.remote, str(self.local))
                    self.assertEqual(self.local.read_bytes(), valid)
                    self.local.unlink()
                    self.outcomes = [corrupt] * 10
                    with self.assertRaises(RuntimeError):
                        fetch(self.remote, str(self.local))
                    self.assertFalse(self.local.exists())
            self.local.write_bytes(valid)


@unittest.skipUnless(shutil.which('mrstats'), 'MRtrix is not installed')
class RealImageValidationTest(unittest.TestCase):
    def test_complete_and_truncated_mif_payloads(self):
        header = (b'mrtrix image\ndim: 2,2,2\nvox: 1,1,1\nlayout: +0,+1,+2\n'
                  b'datatype: Float32LE\nfile: . 256\nEND\n').ljust(256, b'\0')
        complete = header + struct.pack('<8f', *range(8))
        truncated = header + struct.pack('<f', 0)
        real_run = subprocess.run
        for number in (2, 3):
            with self.subTest(notebook=number), tempfile.TemporaryDirectory() as directory:
                local = Path(directory) / 'image.mif'
                fetch = load_helper(number)
                downloads = []

                def run(args, **kwargs):
                    if args[0] == 'osf':
                        downloads.append(args)
                        Path(args[-1]).write_bytes(complete)
                        return subprocess.CompletedProcess(args, 0)
                    return real_run(args, **kwargs)

                with patch('subprocess.run', side_effect=run):
                    local.write_bytes(complete)
                    fetch('fod/image.mif', str(local))
                    self.assertEqual(downloads, [])
                    local.write_bytes(truncated)
                    fetch('fod/image.mif', str(local))
                self.assertEqual(local.read_bytes(), complete)
                self.assertEqual(len(downloads), 1)
                saved = list(Path(directory).glob('*.invalid'))
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0].read_bytes(), truncated)


if __name__ == '__main__':
    unittest.main()
