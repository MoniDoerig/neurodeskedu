#!/usr/bin/env python3
"""
Promote cached executed notebooks from HuggingFace branches instead of re-executing.

Used on main branch pushes: if a notebook's source matches a cached source on any
review/* branch, the corresponding executed notebook is downloaded and used directly,
avoiding redundant execution.

Usage:
    python promote_notebook.py <notebook_path>

    Exit code 0: promotion succeeded, executed notebook written to <notebook_path>
    Exit code 1: no matching cache found, caller should execute normally

Environment variables:
    HF_TOKEN: Hugging Face token with read access
    HF_REPO: Hugging Face dataset repo (default: neurodeskorg/neurodeskedu)
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path


def _retry(fn, description="operation", max_attempts=3, backoff=5):
    """Retry a callable with exponential backoff on transient failures."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            err_str = str(e)
            status = getattr(getattr(e, "response", None), "status_code", None)
            transient = status in (403, 429, 500, 502, 503, 504) or \
                "ConnectionError" in type(e).__name__ or \
                "Timeout" in type(e).__name__
            if transient and attempt < max_attempts:
                wait = backoff * (2 ** (attempt - 1))
                print(f"    Retry {attempt}/{max_attempts} for {description} "
                      f"(error: {err_str[:120]}), waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


# Cell-level keys that change between executions without author action
_CELL_SKIP_KEYS = {"execution_count", "outputs", "id"}

# Cell metadata keys that are execution artifacts
_CELL_META_SKIP_KEYS = {"ExecuteTime", "execution"}


def _strip_cell(cell: dict) -> dict:
    """Return a copy of cell with execution artifacts removed."""
    stripped = {k: v for k, v in cell.items() if k not in _CELL_SKIP_KEYS}
    if "metadata" in stripped:
        stripped["metadata"] = {
            k: v for k, v in stripped["metadata"].items()
            if k not in _CELL_META_SKIP_KEYS
        }
    return stripped


def extract_notebook_fingerprint(notebook_path: str) -> dict:
    """Extract comparable notebook content, stripping only execution artifacts.

    Keeps notebook-level metadata (authors, kernelspec, etc.) and all cell
    content — only removes fields that change on re-execution.
    """
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    return {
        "metadata": nb.get("metadata", {}),
        "cells": [_strip_cell(c) for c in nb.get("cells", [])],
    }


def notebooks_match(local_path: str, remote_path: str) -> bool:
    """Compare two notebooks, ignoring only execution artifacts."""
    try:
        local_fp = extract_notebook_fingerprint(local_path)
        remote_fp = extract_notebook_fingerprint(remote_path)
        return local_fp == remote_fp
    except Exception as e:
        print(f"    Comparison failed: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: promote_notebook.py <notebook_path>")
        sys.exit(1)

    notebook_path = sys.argv[1]  # e.g. books/examples/functional_imaging/intro.ipynb
    hf_repo = os.environ.get("HF_REPO", "neurodeskorg/neurodeskedu")
    hf_source_path = notebook_path  # source keeps same filename on HF
    # outputs/ mirror of books/ — same filename, different prefix
    hf_outputs_path = "outputs/" + notebook_path.removeprefix("books/")

    print(f"Checking promotion cache for: {notebook_path}")
    print(f"  HF source path: {hf_source_path}")
    print(f"  HF outputs path: {hf_outputs_path}")

    try:
        from huggingface_hub import HfApi, hf_hub_download, file_exists
    except ImportError:
        print("ERROR: huggingface_hub not installed")
        sys.exit(1)

    api = HfApi()

    # List all HF branches matching review/* pattern
    try:
        refs = _retry(
            lambda: api.list_repo_refs(hf_repo, repo_type="dataset"),
            description="list HF branches",
        )
        review_branches = [
            b.name for b in refs.branches
            if b.name.startswith("review/")
        ]
    except Exception as e:
        print(f"  Could not list HF branches: {e}")
        sys.exit(1)

    if not review_branches:
        print("  No review/* branches found on HF")
        sys.exit(1)

    print(f"  Found {len(review_branches)} review branch(es): {review_branches}")

    for branch in review_branches:
        print(f"  Checking branch: {branch}")

        # Check if source snapshot exists on this branch
        try:
            exists = _retry(
                lambda b=branch: file_exists(hf_repo, hf_source_path, repo_type="dataset", revision=b),
                description=f"check source on {branch}",
            )
            if not exists:
                print(f"    No source snapshot found")
                continue
        except Exception:
            continue

        # Download the source snapshot and compare
        try:
            remote_source = _retry(
                lambda b=branch: hf_hub_download(
                    hf_repo, hf_source_path,
                    repo_type="dataset", revision=b,
                ),
                description=f"download source from {branch}",
            )
        except Exception as e:
            print(f"    Could not download source: {e}")
            continue

        if not notebooks_match(notebook_path, remote_source):
            print(f"    Source mismatch")
            continue

        # Source matches! Download the outputs notebook
        print(f"    Source matches! Downloading outputs notebook...")
        try:
            out_exists = _retry(
                lambda b=branch: file_exists(hf_repo, hf_outputs_path, repo_type="dataset", revision=b),
                description=f"check outputs on {branch}",
            )
            if not out_exists:
                print(f"    No outputs notebook found on this branch")
                continue

            remote_outputs = _retry(
                lambda b=branch: hf_hub_download(
                    hf_repo, hf_outputs_path,
                    repo_type="dataset", revision=b,
                ),
                description=f"download outputs from {branch}",
            )
            shutil.copy(remote_outputs, notebook_path)
            print(f"    Promoted from branch '{branch}' -> {notebook_path}")
            sys.exit(0)

        except Exception as e:
            print(f"    Could not download executed notebook: {e}")
            continue

    print("  No matching cache found across any review branch")
    sys.exit(1)


if __name__ == "__main__":
    main()
