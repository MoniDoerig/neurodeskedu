#!/usr/bin/env python3
"""Validate image references in Markdown and notebook tutorials.

Run from the repository root. HTML comments are excluded because contributor
templates contain example image paths that are not published content.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from check_notebook_images import extract_image_references


def references(path: Path):
    if path.suffix == ".ipynb":
        notebook = json.loads(path.read_text(encoding="utf-8"))
    else:
        notebook = {"cells": [{"cell_type": "markdown", "source": path.read_text(encoding="utf-8")} ]}
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = cell.get("source", "")
            source = "".join(source) if isinstance(source, list) else source
            cell["source"] = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    return extract_image_references(notebook)


def check(paths: list[Path], books: Path) -> tuple[int, list[str]]:
    count = 0
    problems = []
    books = books.resolve()
    sources = set()
    for path in paths:
        sources.update(path.rglob("*.md") if path.is_dir() else [path])
        if path.is_dir():
            sources.update(path.rglob("*.ipynb"))
    for source in sorted(sources):
        if any(part.startswith(("_", ".")) for part in source.relative_to(books).parts):
            continue
        for ref in references(source):
            url = urlsplit(ref.target)
            if url.scheme or url.netloc or ref.target.startswith(("#", "attachment:")):
                continue
            if ref.syntax == "IPython Image":
                continue  # Runtime-generated outputs use the notebook checker.
            target = unquote(url.path)
            candidate = (books / target.lstrip("/") if target.startswith("/") else source.parent / target).resolve()
            count += 1
            if not candidate.is_relative_to(books) or not candidate.is_file():
                problems.append(f"{source.relative_to(books)}: cell {ref.cell_index + 1}: missing image {ref.target}")
            else:
                # Also catch spelling that only works on case-insensitive macOS.
                current = books
                for part in candidate.relative_to(books).parts:
                    if part not in {child.name for child in current.iterdir()}:
                        problems.append(f"{source}: image path has incorrect case: {ref.target}")
                        break
                    current = current / part
    return count, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("books/tutorials")])
    parser.add_argument("--books-dir", type=Path, default=Path("books"))
    args = parser.parse_args()
    count, problems = check([p.resolve() for p in args.paths], args.books_dir)
    for problem in problems:
        print(problem)
    print(f"Checked {count} local image references; {len(problems)} problems.")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
