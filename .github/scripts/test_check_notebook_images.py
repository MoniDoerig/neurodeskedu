#!/usr/bin/env python3
"""Tests for the notebook image validator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from check_notebook_images import validate_notebook


class NotebookImageValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.books = self.root / "books"
        self.notebook_dir = self.books / "examples" / "demo"
        self.notebook_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_notebook(self, cells: list[dict]) -> Path:
        path = self.notebook_dir / "demo.ipynb"
        path.write_text(json.dumps({"cells": cells}), encoding="utf-8")
        return path

    def validate(self, cells: list[dict]):
        return validate_notebook(self.write_notebook(cells), self.books)

    def test_supported_local_references_resolve(self) -> None:
        assets = self.notebook_dir / "demo_assets"
        assets.mkdir()
        (assets / "plot.png").write_bytes(b"png")
        (self.books / "static").mkdir()
        (self.books / "static" / "logo.png").write_bytes(b"png")
        cells = [
            {
                "cell_type": "markdown",
                "source": (
                    "![Markdown](demo_assets/plot.png)\n"
                    '<img src="demo_assets/plot.png">\n'
                    ":::{figure} demo_assets/plot.png\n:::\n"
                    "![Root static](/static/logo.png)\n"
                    "![Remote](https://example.org/plot.png)\n"
                ),
            },
            {
                "cell_type": "code",
                "source": "Image(filename='demo_assets/plot.png')",
            },
        ]

        count, problems = self.validate(cells)

        self.assertEqual(count, 5)
        self.assertEqual(problems, [])

    def test_missing_image_fails(self) -> None:
        count, problems = self.validate(
            [{"cell_type": "markdown", "source": "![Missing](demo_assets/nope.png)"}]
        )

        self.assertEqual(count, 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("image is absent", problems[0].message)

    def test_upward_traversal_fails_even_when_image_exists(self) -> None:
        static = self.books / "static"
        static.mkdir()
        (static / "plot.png").write_bytes(b"png")

        _, problems = self.validate(
            [{"cell_type": "markdown", "source": "![Plot](../../../static/plot.png)"}]
        )

        self.assertEqual(len(problems), 1)
        self.assertEqual(
            problems[0].message, "relative image leaves the notebook directory"
        )

    def test_notebook_attachments_are_checked(self) -> None:
        cells = [
            {
                "cell_type": "markdown",
                "source": "![Present](attachment:present.png) ![Missing](attachment:missing.png)",
                "attachments": {"present.png": {"image/png": "AAAA"}},
            }
        ]

        count, problems = self.validate(cells)

        self.assertEqual(count, 2)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0].target, "attachment:missing.png")

    def test_generated_code_image_does_not_need_to_exist(self) -> None:
        count, problems = self.validate(
            [
                {
                    "cell_type": "code",
                    "source": "display(Image(filename='./output/generated.png'))",
                }
            ]
        )

        self.assertEqual(count, 0)
        self.assertEqual(problems, [])

    def test_missing_code_asset_fails(self) -> None:
        count, problems = self.validate(
            [
                {
                    "cell_type": "code",
                    "source": "display(Image(filename='demo_assets/missing.png'))",
                }
            ]
        )

        self.assertEqual(count, 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("image is absent", problems[0].message)

    def test_image_example_inside_code_span_is_ignored(self) -> None:
        count, problems = self.validate(
            [
                {
                    "cell_type": "markdown",
                    "source": "Use `<img src='placeholder.png'>` as an example.",
                }
            ]
        )

        self.assertEqual(count, 0)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
