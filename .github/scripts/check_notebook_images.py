#!/usr/bin/env python3
"""Check that local images referenced by notebooks are portable and present."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


MARKDOWN_IMAGE = re.compile(
    r"!\[[^\]]*\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))",
    re.MULTILINE,
)
REFERENCE_DEFINITION = re.compile(
    r"^\s*\[([^\]]+)\]:\s*(?:<([^>]+)>|(\S+))", re.MULTILINE
)
REFERENCE_IMAGE = re.compile(r"!\[([^\]]*)\]\[([^\]]*)\]")
MYST_IMAGE = re.compile(
    r"^\s*(?:`{3,}|:{3,})\{(?:figure|image)\}\s+(.+?)\s*$", re.MULTILINE
)
RST_IMAGE = re.compile(r"^\s*\.\.\s+(?:figure|image)::\s+(.+?)\s*$", re.MULTILINE)
PYTHON_IMAGE = re.compile(
    r"\bImage\s*\([^)]*?\bfilename\s*=\s*(['\"])(?P<target>.+?)\1",
    re.DOTALL,
)


@dataclass(frozen=True)
class ImageReference:
    cell_index: int
    target: str
    syntax: str


@dataclass(frozen=True)
class Problem:
    notebook: Path
    cell_index: int | None
    target: str | None
    message: str

    def format(self, root: Path) -> str:
        try:
            notebook = self.notebook.relative_to(root)
        except ValueError:
            notebook = self.notebook
        location = str(notebook)
        if self.cell_index is not None:
            location += f":cell {self.cell_index + 1}"
        target = f" [{self.target}]" if self.target else ""
        return f"{location}{target}: {self.message}"


class _ImageHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        for name, value in attrs:
            if name.lower() == "src" and value:
                self.targets.append(value)


def _cell_source(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def _clean_directive_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1].strip()
    return target.split(maxsplit=1)[0]


def _without_markdown_code(source: str) -> str:
    """Hide code spans and fenced blocks from Markdown/HTML image parsing."""
    lines = source.splitlines(keepends=True)
    masked: list[str] = []
    fence: tuple[str, int] | None = None
    for line in lines:
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence is None and match:
            marker = match.group(1)
            fence = (marker[0], len(marker))
            masked.append("\n" if line.endswith("\n") else "")
        elif fence is not None:
            if re.match(re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*$", stripped):
                fence = None
            masked.append("\n" if line.endswith("\n") else "")
        else:
            masked.append(line)

    without_fences = "".join(masked)
    return re.sub(r"(?<!`)`[^`\n]+`(?!`)", "", without_fences)


def _markdown_references(source: str, cell_index: int) -> list[ImageReference]:
    references: list[ImageReference] = []

    for pattern, syntax in ((MYST_IMAGE, "MyST image"), (RST_IMAGE, "reST image")):
        references.extend(
            ImageReference(cell_index, _clean_directive_target(match.group(1)), syntax)
            for match in pattern.finditer(source)
        )

    source = _without_markdown_code(source)

    for match in MARKDOWN_IMAGE.finditer(source):
        references.append(
            ImageReference(
                cell_index,
                match.group("angle") or match.group("plain"),
                "Markdown image",
            )
        )

    definitions = {
        match.group(1).strip().casefold(): match.group(2) or match.group(3)
        for match in REFERENCE_DEFINITION.finditer(source)
    }
    for match in REFERENCE_IMAGE.finditer(source):
        label = (match.group(2) or match.group(1)).strip().casefold()
        if label in definitions:
            references.append(
                ImageReference(cell_index, definitions[label], "Markdown reference image")
            )

    parser = _ImageHTMLParser()
    parser.feed(source)
    references.extend(
        ImageReference(cell_index, target, "HTML image") for target in parser.targets
    )

    return references


def extract_image_references(notebook: dict) -> list[ImageReference]:
    references: list[ImageReference] = []
    for cell_index, cell in enumerate(notebook.get("cells", [])):
        source = _cell_source(cell)
        if cell.get("cell_type") == "markdown":
            references.extend(_markdown_references(source, cell_index))
        elif cell.get("cell_type") == "code":
            references.extend(
                ImageReference(cell_index, match.group("target"), "IPython Image")
                for match in PYTHON_IMAGE.finditer(source)
            )
    return references


def _is_external(target: str) -> bool:
    parsed = urlsplit(target)
    return bool(parsed.scheme or parsed.netloc or target.startswith("#"))


def validate_notebook(notebook_path: Path, books_dir: Path) -> tuple[int, list[Problem]]:
    try:
        with notebook_path.open(encoding="utf-8") as notebook_file:
            notebook = json.load(notebook_file)
    except (OSError, json.JSONDecodeError) as error:
        return 0, [Problem(notebook_path, None, None, f"cannot read notebook: {error}")]

    references = extract_image_references(notebook)
    problems: list[Problem] = []
    local_count = 0
    notebook_dir = notebook_path.parent.resolve()
    books_dir = books_dir.resolve()

    for reference in references:
        target = reference.target.strip()
        if not target:
            continue

        if target.startswith("attachment:"):
            local_count += 1
            attachment = target.removeprefix("attachment:")
            cells = notebook.get("cells", [])
            attachments = cells[reference.cell_index].get("attachments", {})
            if attachment not in attachments:
                problems.append(
                    Problem(
                        notebook_path,
                        reference.cell_index,
                        target,
                        "notebook attachment is absent",
                    )
                )
            continue

        if _is_external(target):
            continue

        url_path = unquote(urlsplit(target).path).replace("\\", "/")
        path_parts = Path(url_path).parts
        if reference.syntax == "IPython Image" and not (
            ".." in path_parts or any(part.endswith("_assets") for part in path_parts)
        ):
            # Image(filename=...) often displays an output produced by an earlier
            # cell. Only *_assets paths and legacy upward paths describe files
            # that must exist in a fresh checkout.
            continue

        local_count += 1
        if url_path.startswith("/"):
            candidate = (books_dir / url_path.lstrip("/")).resolve()
        else:
            candidate = (notebook_dir / url_path).resolve()
            if not candidate.is_relative_to(notebook_dir):
                problems.append(
                    Problem(
                        notebook_path,
                        reference.cell_index,
                        target,
                        "relative image leaves the notebook directory",
                    )
                )
                continue

        if not candidate.is_relative_to(books_dir):
            problems.append(
                Problem(
                    notebook_path,
                    reference.cell_index,
                    target,
                    "image resolves outside books/",
                )
            )
        elif not candidate.is_file():
            problems.append(
                Problem(
                    notebook_path,
                    reference.cell_index,
                    target,
                    f"image is absent at {candidate.relative_to(books_dir)}",
                )
            )

    return local_count, problems


def _notebook_paths(inputs: list[Path]) -> list[Path]:
    notebooks: set[Path] = set()
    for path in inputs:
        if path.is_dir():
            notebooks.update(path.rglob("*.ipynb"))
        elif path.suffix == ".ipynb":
            notebooks.add(path)
    return sorted(notebooks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("books")])
    parser.add_argument("--books-dir", type=Path, default=Path("books"))
    args = parser.parse_args(argv)

    notebooks = _notebook_paths(args.paths)
    problems: list[Problem] = []
    reference_count = 0
    for notebook in notebooks:
        count, notebook_problems = validate_notebook(notebook, args.books_dir)
        reference_count += count
        problems.extend(notebook_problems)

    root = Path.cwd().resolve()
    if problems:
        print(f"Found {len(problems)} notebook image problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem.format(root)}", file=sys.stderr)
        return 1

    print(
        f"Checked {reference_count} local image reference(s) in "
        f"{len(notebooks)} notebook(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
