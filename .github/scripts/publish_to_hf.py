#!/usr/bin/env python3
"""
Pre-execution transform: Upload local files to Hugging Face and rewrite notebook paths to URLs.

This script runs BEFORE notebook execution to:
1. Scan notebook cells for ipyniivue load_volumes() calls with local paths
2. Upload referenced files to Hugging Face
3. Rewrite cell source: "path" -> "url" with HF URLs
4. Save modified notebook for execution

This way ipyniivue fetches from HF URLs during execution, avoiding embedded data.

Usage:
    python publish_to_hf.py <notebook.ipynb> [--working-dir <dir>]

Environment variables:
    HF_TOKEN: Hugging Face token with write access
    HF_REPO: Hugging Face dataset repo (default: neurodeskorg/neurodeskedu)
    DRY_RUN: If "true", skip upload and just show what would be done
"""

import json
import os
import sys
import re
import hashlib
from pathlib import Path

# Hugging Face configuration
HF_REPO = os.environ.get("HF_REPO", "neurodeskorg/neurodeskedu")
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"

# File extensions that ipyniivue can load
VOLUME_EXTENSIONS = {".nii.gz", ".nii", ".mgz", ".mgh"}
MESH_EXTENSIONS = {".pial", ".white", ".inflated", ".sphere", ".surf", ".gii"}
ALL_EXTENSIONS = VOLUME_EXTENSIONS | MESH_EXTENSIONS


def get_file_hash(filepath: Path) -> str:
    """Generate a short hash of file content for deduplication."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def upload_to_hf(filepath: Path, path_in_repo: str) -> str:
    """Upload file to Hugging Face and return the URL."""
    url = f"{HF_BASE_URL}/{path_in_repo}"

    if DRY_RUN:
        print(f"  [DRY RUN] Would upload: {filepath} -> {path_in_repo}")
        return url

    try:
        from huggingface_hub import upload_file, file_exists

        # Check if file already exists (skip upload if so)
        if file_exists(HF_REPO, path_in_repo, repo_type="dataset"):
            print(f"  Already exists: {path_in_repo}")
            return url

        print(f"  Uploading: {filepath.name} -> {path_in_repo}")

        upload_file(
            path_or_fileobj=str(filepath),
            path_in_repo=path_in_repo,
            repo_id=HF_REPO,
            repo_type="dataset",
            commit_message=f"Add data: {path_in_repo}",
        )

        return url

    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR uploading {filepath}: {e}")
        raise


def find_niivue_paths(cell_source: str) -> list[tuple[str, int, int]]:
    """
    Find ipyniivue path references in cell source.

    Returns list of (path_string, start_pos, end_pos) tuples.
    """
    paths = []

    # Pattern: "path": "./something.nii.gz" or 'path': './something.nii.gz'
    # Also matches path with variables or f-strings, but we only transform literal strings
    pattern = r'"path"\s*:\s*"([^"]+)"|\'path\'\s*:\s*\'([^\']+)\''

    for match in re.finditer(pattern, cell_source):
        path = match.group(1) or match.group(2)

        # Check if it looks like a file path (not a URL, not a variable)
        if path and not path.startswith(("http://", "https://", "{")):
            # Check if it has a supported extension
            path_lower = path.lower()
            if any(path_lower.endswith(ext) for ext in ALL_EXTENSIONS):
                paths.append((path, match.start(), match.end()))

    return paths


def transform_cell(cell_source: str, working_dir: Path, notebook_hf_prefix: str) -> tuple[str, list[dict]]:
    """
    Transform cell source, replacing local paths with HF URLs.

    Returns (new_source, list of uploaded files info).
    """
    paths = find_niivue_paths(cell_source)

    if not paths:
        return cell_source, []

    uploaded = []
    new_source = cell_source
    offset = 0  # Track position shifts from replacements

    for path_str, start, end in paths:
        # Resolve the local file path
        local_path = (working_dir / path_str).resolve()

        if not local_path.exists():
            print(f"  WARNING: File not found: {path_str} (resolved to {local_path})")
            continue

        # Generate HF path with content hash for deduplication
        file_hash = get_file_hash(local_path)
        # Sanitize filename (replace spaces, special chars)
        safe_name = re.sub(r'[^\w\-.]', '_', local_path.name)
        hf_filename = f"{local_path.stem}_{file_hash}{local_path.suffix}"
        if local_path.suffix == ".gz" and local_path.stem.endswith(".nii"):
            # Handle .nii.gz properly
            hf_filename = f"{local_path.stem[:-4]}_{file_hash}.nii.gz"

        hf_path = f"{notebook_hf_prefix}/{hf_filename}"

        # Upload to HF
        hf_url = upload_to_hf(local_path, hf_path)

        uploaded.append({
            "local_path": str(local_path),
            "hf_path": hf_path,
            "hf_url": hf_url,
            "size_bytes": local_path.stat().st_size,
        })

        # Replace "path": "..." with "url": "..."
        # Find the exact match text to replace
        original_text = cell_source[start:end]
        # Determine quote style used
        if original_text.startswith('"path"'):
            new_text = f'"url": "{hf_url}"'
        else:
            new_text = f"'url': '{hf_url}'"

        # Apply replacement with offset tracking
        adj_start = start + offset
        adj_end = end + offset
        new_source = new_source[:adj_start] + new_text + new_source[adj_end:]
        offset += len(new_text) - len(original_text)

    return new_source, uploaded


def transform_notebook(notebook_path: str, working_dir: str = None) -> dict:
    """
    Transform notebook: upload local files to HF and rewrite paths to URLs.

    This modifies the notebook in place (for CI use).
    """
    notebook_path = Path(notebook_path)

    if working_dir:
        working_dir = Path(working_dir)
    else:
        working_dir = notebook_path.parent

    print(f"\nProcessing: {notebook_path}")
    print(f"Working dir: {working_dir}")

    # Load notebook
    with open(notebook_path) as f:
        nb = json.load(f)

    # Determine HF path prefix based on notebook location
    # e.g., "books/examples/structural_imaging/FSL_course_bet.ipynb" -> "examples/structural_imaging/FSL_course_bet"
    notebook_rel = str(notebook_path.with_suffix(""))
    if notebook_rel.startswith("books/"):
        notebook_rel = notebook_rel[6:]
    notebook_hf_prefix = notebook_rel

    print(f"HF prefix: {notebook_hf_prefix}")

    all_uploaded = []
    cells_modified = 0

    # Process each code cell
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        # Get cell source as string
        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source

        # Skip cells without ipyniivue patterns
        if "load_volumes" not in source_str and "load_meshes" not in source_str:
            continue

        print(f"\nCell {i}: Found ipyniivue usage")

        # Transform the cell
        new_source, uploaded = transform_cell(source_str, working_dir, notebook_hf_prefix)

        if uploaded:
            # Update cell source
            cell["source"] = new_source
            cells_modified += 1
            all_uploaded.extend(uploaded)

            for u in uploaded:
                print(f"  {Path(u['local_path']).name} -> {u['hf_url']}")

    if cells_modified == 0:
        print("  No paths to transform")
        return {"transformed": False, "reason": "no_paths"}

    # Save modified notebook
    with open(notebook_path, "w") as f:
        json.dump(nb, f, indent=1)

    print(f"\nSummary:")
    print(f"  Cells modified: {cells_modified}")
    print(f"  Files uploaded: {len(all_uploaded)}")
    total_size = sum(u["size_bytes"] for u in all_uploaded)
    print(f"  Total data moved to HF: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")

    return {
        "transformed": True,
        "cells_modified": cells_modified,
        "files_uploaded": len(all_uploaded),
        "uploaded_files": all_uploaded,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", help="Path to notebook file")
    parser.add_argument("--working-dir", "-w", help="Working directory for resolving paths")

    args = parser.parse_args()

    if not os.path.exists(args.notebook):
        print(f"ERROR: Notebook not found: {args.notebook}")
        sys.exit(1)

    # Check for HF token
    if not DRY_RUN and not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set. Uploads will fail.")

    result = transform_notebook(args.notebook, args.working_dir)

    if result["transformed"]:
        print(f"\nSuccess! Notebook transformed for HF URLs.")
    else:
        print(f"\nNo transformation needed: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
