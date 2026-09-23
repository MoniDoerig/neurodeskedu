"""Exercise real notebook control cells across two fresh kernels, without imaging tools."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import nbformat
from nbclient.exceptions import CellExecutionError

from execute_notebook import execute_notebook

ROOT = Path(__file__).resolve().parents[2]


def source_cell(name, prefix):
    notebook = nbformat.read(ROOT / f"books/examples/structural_imaging/{name}.ipynb", 4)
    return deepcopy(next(c for c in notebook.cells if c.cell_type == "code" and c.source.startswith(prefix)))


class PublicationPassTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "tutorial.ipynb"

    def save(self, cells):
        nbformat.write(nbformat.v4.new_notebook(cells=cells), self.path)

    def fixture(self, name):
        setup = '''from pathlib import Path
from types import SimpleNamespace
import nibabel as nib
import numpy as np
RUN_RECON = RUN_SYNCRO = True
SUBJECTS_DIR = Path("subjects")
SUBJECT_ID = "example"
SUBJECT_DIR = SUBJECTS_DIR / SUBJECT_ID
INPUT_SCAN = Path("input.nii.gz")
THREADS = 1
OUTPUT_DIR = Path("syncro_output")
anat, lesion = Path("scan.nii.gz"), Path("lesion.nii.gz")
FORCE_GPU, SYNCRO_VERSION = "false", "fixture"
MNI_TEMPLATE = Path("template.nii.gz")
nib.save(nib.Nifti1Image(np.ones((2, 2, 2)), np.eye(4)), MNI_TEMPLATE)

def run(command, check):
    assert check
    with Path("commands.txt").open("a") as log:
        log.write(command[0] + "\\n")
    if command[0] == "recon-all":
        files = ["mri/orig.mgz", "mri/brainmask.mgz", "mri/aseg.mgz",
                 "surf/lh.white", "surf/rh.white", "surf/lh.pial", "surf/rh.pial",
                 "stats/aseg.stats", "stats/lh.aparc.stats", "stats/rh.aparc.stats"]
        for name in files + ["scripts/recon-all.done"]:
            path = SUBJECT_DIR / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("END_TIME fixture")
    else:
        for name in ("wbt1" + anat.name, "w" + anat.name, "w" + lesion.name):
            nib.save(nib.load(MNI_TEMPLATE), OUTPUT_DIR / name)

subprocess = SimpleNamespace(run=run)
'''
        prefixes = {
            "freesurfer": ["SUBJECTS_DIR.mkdir", "if RUN_RECON:", "scripts_dir =", "expected_files ="],
            "SYNcro": ["completion_file =", "if RUN_SYNCRO:", "warped_synth_t1 =", "for path in (warped_synth_t1", "normalized_mask_image ="],
        }
        cells = [nbformat.v4.new_code_cell(setup)]
        cells.extend(source_cell(name, prefix) for prefix in prefixes[name])
        cells.append(nbformat.v4.new_code_cell('Path("display.txt").write_text("rendered")'))
        self.save(cells)

    def test_both_notebooks_process_once_and_render_twice(self):
        for name in ("freesurfer", "SYNcro"):
            with self.subTest(notebook=name):
                self.fixture(name)
                execute_notebook(self.path, timeout=30)
                first = (self.root / "commands.txt").read_text()
                self.assertTrue((self.root / "display.txt").is_file())
                (self.root / "display.txt").unlink()
                execute_notebook(self.path, publication_pass=True, timeout=30)
                self.assertEqual((self.root / "commands.txt").read_text(), first)
                self.assertTrue((self.root / "display.txt").is_file())
                notebook = nbformat.read(self.path, 4)
                self.assertFalse(any("skip-execution" in c.metadata.get("tags", []) for c in notebook.cells))

    def test_missing_results_still_fail_on_publication_pass(self):
        for name, missing in (("freesurfer", "subjects/example/mri/aseg.mgz"),
                              ("SYNcro", "syncro_output/wlesion.nii.gz")):
            with self.subTest(notebook=name):
                self.fixture(name)
                execute_notebook(self.path, timeout=30)
                (self.root / missing).unlink()
                (self.root / "display.txt").unlink()
                with self.assertRaises(CellExecutionError):
                    execute_notebook(self.path, publication_pass=True, timeout=30)
                self.assertFalse((self.root / "display.txt").exists())

    def test_existing_output_guard_stops_before_processing(self):
        for name, output in (("freesurfer", "subjects/example"), ("SYNcro", "syncro_output")):
            with self.subTest(notebook=name):
                self.fixture(name)
                (self.root / output).mkdir(parents=True)
                with self.assertRaises(CellExecutionError):
                    execute_notebook(self.path, timeout=30)
                self.assertFalse((self.root / "commands.txt").exists())
                self.assertFalse((self.root / "display.txt").exists())

    def test_errors_are_saved_and_stale_outputs_cleared(self):
        stale = nbformat.v4.new_code_cell('Path("should-not-run").touch()')
        stale.outputs = [nbformat.v4.new_output("stream", name="stdout", text="old output")]
        failure = nbformat.v4.new_code_cell('raise RuntimeError("stop here")', metadata={"tags": ["raises-exception"]})
        self.save([failure, stale])
        with self.assertRaises(CellExecutionError):
            execute_notebook(self.path, timeout=30)
        saved = nbformat.read(self.path, 4)
        self.assertEqual(saved.cells[0].outputs[-1].ename, "RuntimeError")
        self.assertEqual(saved.cells[1].outputs, [])
        self.assertIsNone(saved.cells[1].execution_count)
        self.assertFalse((self.root / "should-not-run").exists())

    def test_existing_skip_execution_tag_is_respected_in_both_passes(self):
        self.save([nbformat.v4.new_code_cell('raise RuntimeError("must stay skipped")', metadata={"tags": ["skip-execution"]})])
        execute_notebook(self.path, timeout=30)
        execute_notebook(self.path, publication_pass=True, timeout=30)
        self.assertEqual(nbformat.read(self.path, 4).cells[0].metadata.tags, ["skip-execution"])


if __name__ == "__main__":
    unittest.main()
