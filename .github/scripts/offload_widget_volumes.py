#!/usr/bin/env python3
"""Move NiiVue data embedded in saved widget state to HuggingFace and load it by URL.

publish_to_hf.py rewrites literal paths in notebook code before the second execution,
but paths built at runtime (variables, f-strings, temporary files, AFNI HEAD/BRIK pairs)
still end up as base64 buffers in the saved widget state. This pass works on that state,
so it catches every embedded file however the notebook produced it.

Usage:
    python offload_widget_volumes.py [--book books]

Environment variables are those of publish_to_hf.py (HF_TOKEN, HF_REPO, HF_BRANCH).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Callable

import publish_to_hf as hf

# ipyniivue file fields and the URL fields that load the same file instead.
URL_FIELDS = {"path": "url", "paired_img_path": "paired_img_url"}
EXTENSIONS = sorted({*hf.COMPOUND_EXTENSIONS, *hf.NIIVUE_EXTENSIONS, ".BRIK"}, key=len, reverse=True)


def split_name(name: str) -> tuple[str, str]:
    for ext in EXTENSIONS:
        if name.lower().endswith(ext.lower()):
            return name[:-len(ext)], name[-len(ext):]
    path = Path(name)
    return path.stem, path.suffix


def offload(notebook: dict, prefix: str, upload: Callable[[bytes, str], str]) -> int:
    """Replace embedded NiiVue file buffers with URLs returned by ``upload``."""
    state = (notebook.get("metadata", {}).get("widgets", {})
             .get("application/vnd.jupyter.widget-state+json", {}).get("state", {}))
    moved = 0
    for model in state.values():
        fields = model.get("state", {})
        kept = []
        for buffer in model.get("buffers", []):
            field = buffer.get("path", [None])[0]
            if (buffer.get("path") != [field, "data"] or field not in URL_FIELDS
                    or URL_FIELDS[field] not in fields or buffer.get("encoding") != "base64"):
                kept.append(buffer)
                continue
            data = base64.b64decode(buffer["data"])
            stem, ext = split_name(fields[field]["name"])
            digest = hashlib.sha256(data).hexdigest()[:12]
            fields[URL_FIELDS[field]] = upload(data, f"{prefix}/{stem}_{digest}{ext}")
            fields[field] = {"data": None, "name": None}
            moved += 1
        if "buffers" in model:
            model["buffers"] = kept
    return moved


def upload_to_hf(data: bytes, path_in_repo: str) -> str:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / Path(path_in_repo).name
        path.write_bytes(data)
        return hf.upload_to_hf(path, path_in_repo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--book", type=Path, default=Path("books"))
    args = parser.parse_args()
    hf.ensure_gitattributes(set(EXTENSIONS))
    total = 0
    for path in sorted(args.book.rglob("*.ipynb")):
        if "_build" in path.parts or ".ipynb_checkpoints" in path.parts:
            continue
        notebook = json.loads(path.read_text())
        prefix = "data/" + path.relative_to(args.book).with_suffix("").as_posix()
        try:
            moved = offload(notebook, prefix, upload_to_hf)
        except Exception as error:
            # The notebook still renders with its data embedded, only larger.
            print(f"::warning::Kept embedded widget data in {path}: {error}")
            continue
        if moved:
            path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
            print(f"{path}: moved {moved} embedded files to HuggingFace")
            total += moved
    print(f"Moved {total} embedded widget files to HuggingFace")


if __name__ == "__main__":
    main()
