import hashlib
import json
import re
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIRECTORY = REPOSITORY_ROOT / "books/examples/diffusion_imaging"


def helper_source(notebook_name):
    notebook = json.loads((NOTEBOOK_DIRECTORY / notebook_name).read_text())
    matching_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if "def download_with_resume" in "".join(cell.get("source", []))
    ]
    if len(matching_cells) != 1:
        raise AssertionError(
            f"Expected one download helper cell in {notebook_name}, "
            f"found {len(matching_cells)}"
        )
    return matching_cells[0]


def markdown_source(notebook_name):
    notebook = json.loads((NOTEBOOK_DIRECTORY / notebook_name).read_text())
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "markdown"
    )


def load_download_helper():
    namespace = {}
    exec(helper_source("DIPY_1.ipynb"), namespace)
    return SimpleNamespace(**namespace)


class TruncatedDownloadHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    payload = bytes(range(256)) * 32
    first_response_size = len(payload) // 3
    range_headers = []

    def do_GET(self):
        range_header = self.headers.get("Range")
        type(self).range_headers.append(range_header)

        if range_header is None:
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.write_chunked(self.payload[: self.first_response_size])
            return

        offset = int(range_header.removeprefix("bytes=").removesuffix("-"))
        self.send_response(206)
        self.send_header(
            "Content-Range",
            f"bytes {offset}-{len(self.payload) - 1}/{len(self.payload)}",
        )
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.write_chunked(self.payload[offset:])

    def write_chunked(self, data):
        self.wfile.write(f"{len(data):x}\r\n".encode())
        self.wfile.write(data)
        self.wfile.write(b"\r\n0\r\n\r\n")

    def log_message(self, _format, *_args):
        pass


class DownloadWithResumeTest(unittest.TestCase):
    def setUp(self):
        TruncatedDownloadHandler.range_headers = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TruncatedDownloadHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()

    def test_resumes_after_a_clean_early_eof(self):
        helper = load_download_helper()
        payload = TruncatedDownloadHandler.payload
        expected_md5 = hashlib.md5(payload).hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "HARDI150.nii.gz"
            result = helper.download_with_resume(
                f"http://127.0.0.1:{self.server.server_port}/dwi.nii.gz",
                destination,
                expected_md5,
                len(payload),
                tries=3,
                delay=0,
            )

            self.assertEqual(result, destination)
            self.assertEqual(destination.read_bytes(), payload)

        self.assertEqual(
            TruncatedDownloadHandler.range_headers,
            [None, f"bytes={TruncatedDownloadHandler.first_response_size}-"],
        )


class NotebookWiringTest(unittest.TestCase):
    def test_both_dipy_notebooks_use_the_same_resumable_download(self):
        dipy_1_source = helper_source("DIPY_1.ipynb")
        dipy_2_source = helper_source("DIPY_2.ipynb")

        self.assertEqual(dipy_1_source, dipy_2_source)
        self.assertIn('headers = {"Range": f"bytes={offset}-"}', dipy_1_source)
        self.assertIn('if name == "stanford_hardi":', dipy_1_source)


class CliDocumentationTest(unittest.TestCase):
    expected_commands = {
        "DIPY_1.ipynb": {
            "dipy_brain_mask",
            "dipy_fit_fwdti",
            "dipy_fit_powermap",
        },
        "DIPY_2.ipynb": {
            "dipy_cluster_streamlines",
            "dipy_fit_force",
            "dipy_fit_msmtcsd",
        },
    }

    def test_documents_every_new_dipy_1_12_command(self):
        command_link = re.compile(
            r"\[`(dipy_[a-z0-9_]+)`\]"
            r"\(https://docs\.dipy\.org/stable/reference_cmd/[^)]+\)"
        )

        for notebook_name, expected_commands in self.expected_commands.items():
            with self.subTest(notebook=notebook_name):
                documented_commands = set(
                    command_link.findall(markdown_source(notebook_name))
                )
                self.assertTrue(
                    expected_commands.issubset(documented_commands),
                    f"Missing command documentation: "
                    f"{sorted(expected_commands - documented_commands)}",
                )

    def test_links_to_the_complete_workflow_catalog(self):
        catalog_url = "https://docs.dipy.org/stable/interfaces/index.html"

        for notebook_name in self.expected_commands:
            with self.subTest(notebook=notebook_name):
                self.assertIn(catalog_url, markdown_source(notebook_name))

    def test_msmt_example_enables_msmt(self):
        source = markdown_source("DIPY_2.ipynb")

        self.assertIn(
            "fits standard single-shell single-tissue CSD by default", source
        )
        self.assertIn("Pass `--use_msmt` to fit multi-shell multi-tissue CSD", source)
        self.assertRegex(source, r"(?m)^dipy_fit_msmtcsd .* --use_msmt(?: |$)")

    def test_dipy_1_toc_matches_the_cli_section_order(self):
        source = markdown_source("DIPY_1.ipynb")

        self.assertLess(
            source.index("[DIPY command-line workflows]"),
            source.index("[Data Preparation]"),
        )


if __name__ == "__main__":
    unittest.main()
