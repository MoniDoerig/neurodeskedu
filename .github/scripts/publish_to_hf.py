#!/usr/bin/env python3
"""
Post-execution transform: Upload local files to Hugging Face and rewrite notebook paths to URLs.

Workflow:
1. First execution downloads data and generates outputs
2. This script scans working directory for niivue-compatible files
3. Uploads files to Hugging Face
4. Rewrites cell source: path -> url (handles both string literals and variable paths)
5. Injects documentation cell with URL mapping
6. Clears outputs for second execution

Usage:
    python publish_to_hf.py <notebook.ipynb> [--working-dir <dir>] [--clear-outputs]

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
NIIVUE_EXTENSIONS = {
    ".nii.gz", ".nii", ".mgz", ".mgh",  # Volumes
    ".pial", ".white", ".inflated", ".sphere", ".surf", ".gii",  # Meshes
    ".trk", ".tck", ".vtk",  # Tractography
    ".HEAD", ".BRIK.gz",  # AFNI
}

# Additional compound extensions to check
COMPOUND_EXTENSIONS = [
    ".nii.gz", ".tt.gz", ".mz3", ".srf.gz", ".smp.gz",
    ".dtseries.nii", ".dscalar.nii", ".BRIK.gz",
]


def get_file_hash(filepath: Path) -> str:
    """Generate a short hash of file content for deduplication."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def is_niivue_file(filepath: Path) -> bool:
    """Check if file has a niivue-compatible extension."""
    name = filepath.name.lower()
    # Check compound extensions first
    for ext in COMPOUND_EXTENSIONS:
        if name.endswith(ext.lower()):
            return True
    # Check simple extensions
    return filepath.suffix.lower() in NIIVUE_EXTENSIONS


def scan_data_files(directory: Path) -> dict[str, Path]:
    """
    Scan directory recursively for niivue-compatible data files.
    Returns dict mapping filename -> full path.
    Excludes common non-data directories.
    """
    # Directories to exclude
    exclude_dirs = {
        ".venv", "venv", ".env", "env",
        "node_modules", ".git", "__pycache__",
        ".cache", ".local", "site-packages",
        "_build", ".ipynb_checkpoints",
    }

    files = {}
    for filepath in directory.rglob("*"):
        # Skip excluded directories
        if any(excluded in filepath.parts for excluded in exclude_dirs):
            continue
        if filepath.is_file() and is_niivue_file(filepath):
            files[filepath.name] = filepath
    return files


def upload_to_hf(filepath: Path, path_in_repo: str) -> str:
    """Upload file to Hugging Face and return the URL."""
    url = f"{HF_BASE_URL}/{path_in_repo}"

    if DRY_RUN:
        print(f"  [DRY RUN] Would upload: {filepath} -> {path_in_repo}")
        return url

    try:
        from huggingface_hub import upload_file, file_exists

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


def transform_cell_paths(cell_source: str, url_mapping: dict[str, str]) -> tuple[str, int]:
    """
    Transform cell source, replacing local paths with HF URLs.

    Handles:
    - String literals: "path": "./data/file.nii.gz"
    - Variable paths: "path": DATA_FOLDER / "file.nii.gz"
    - Keyword args: path=DATA_FOLDER / "file.nii.gz"

    Returns (new_source, count of replacements).
    """
    new_source = cell_source
    replacements = 0

    for filename, hf_url in url_mapping.items():
        # Escape special regex chars in filename
        escaped_filename = re.escape(filename)

        # Pattern 1: "path": "...filename" or 'path': '...filename'
        # Matches string literal paths
        pattern1 = rf'(["\']path["\']\s*:\s*)["\'][^"\']*{escaped_filename}["\']'
        replacement1 = rf'\1"{hf_url}"'.replace("\\1", r"\1")

        # Pattern 2: "path": VARIABLE / "filename" or "path": VARIABLE / 'filename'
        # Matches variable-based paths
        pattern2 = rf'(["\']path["\']\s*:\s*)[A-Za-z_][A-Za-z0-9_]*\s*/\s*["\']?{escaped_filename}["\']?'

        # Pattern 3: path=VARIABLE / "filename" (keyword argument)
        pattern3 = rf'(path\s*=\s*)[A-Za-z_][A-Za-z0-9_]*\s*/\s*["\']?{escaped_filename}["\']?'

        for pattern in [pattern1, pattern2, pattern3]:
            matches = list(re.finditer(pattern, new_source))
            if matches:
                # Replace "path" with "url" and set the URL
                if "path" in pattern:
                    new_source = re.sub(
                        pattern,
                        lambda m: m.group(1).replace("path", "url").replace("'", '"') + f'"{hf_url}"',
                        new_source
                    )
                    replacements += len(matches)

    return new_source, replacements


def create_hf_data_cell(url_mapping: dict[str, str]) -> dict:
    """Create a documentation cell showing HF URL mapping."""
    lines = [
        "# Data uploaded to Hugging Face by CI",
        "# ipyniivue widgets load from these URLs instead of local files.",
        "HF_DATA = {"
    ]
    for filename, url in sorted(url_mapping.items()):
        lines.append(f'    "{filename}": "{url}",')
    lines.append("}")

    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": ["hf-data-urls"]},
        "outputs": [],
        "source": "\n".join(lines)
    }


def clear_notebook_outputs(nb: dict) -> int:
    """Clear all cell outputs and widget state from notebook."""
    cleared = 0

    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            if cell.get("outputs"):
                cell["outputs"] = []
                cleared += 1
            cell["execution_count"] = None

    if "widgets" in nb.get("metadata", {}):
        del nb["metadata"]["widgets"]
        print("  Cleared widget state from metadata")

    return cleared


def find_ipyniivue_import_index(nb: dict) -> int:
    """Find the index of the cell that imports ipyniivue."""
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            if "ipyniivue" in source and "import" in source:
                return i
    return 0


def transform_notebook(notebook_path: str, working_dir: str = None, clear_outputs: bool = False) -> dict:
    """
    Transform notebook: scan for data files, upload to HF, rewrite paths to URLs.
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

    # Determine HF path prefix
    notebook_rel = str(notebook_path.with_suffix(""))
    if notebook_rel.startswith("books/"):
        notebook_rel = notebook_rel[6:]
    notebook_hf_prefix = notebook_rel

    print(f"HF prefix: {notebook_hf_prefix}")

    # Scan for data files
    print("\nScanning for niivue data files...")
    data_files = scan_data_files(working_dir)
    print(f"  Found {len(data_files)} files")

    if not data_files:
        print("  No data files found")
        return {"transformed": False, "reason": "no_data_files"}

    # Upload files and build URL mapping
    print("\nUploading to Hugging Face...")
    url_mapping = {}  # filename -> HF URL
    total_size = 0

    for filename, filepath in data_files.items():
        file_hash = get_file_hash(filepath)

        # Handle compound extensions properly
        stem = filepath.stem
        suffix = filepath.suffix
        for compound in COMPOUND_EXTENSIONS:
            if filename.lower().endswith(compound.lower()):
                stem = filename[:-len(compound)]
                suffix = compound
                break

        hf_filename = f"{stem}_{file_hash}{suffix}"
        hf_path = f"{notebook_hf_prefix}/{hf_filename}"

        hf_url = upload_to_hf(filepath, hf_path)
        url_mapping[filename] = hf_url
        total_size += filepath.stat().st_size

    # Transform cells
    print("\nTransforming notebook cells...")
    cells_modified = 0
    total_replacements = 0

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source

        # Check if cell has ipyniivue usage
        if not any(kw in source_str for kw in ["load_volumes", "load_meshes", "add_volume", "add_mesh", "ipyniivue"]):
            continue

        new_source, replacements = transform_cell_paths(source_str, url_mapping)

        if replacements > 0:
            cell["source"] = new_source
            cells_modified += 1
            total_replacements += replacements
            print(f"  Cell {i}: {replacements} path(s) transformed")

    # Inject HF data documentation cell
    if url_mapping:
        hf_cell = create_hf_data_cell(url_mapping)
        insert_index = find_ipyniivue_import_index(nb) + 1
        nb["cells"].insert(insert_index, hf_cell)
        print(f"\nInjected HF data cell at index {insert_index}")

    # Clear outputs if requested
    outputs_cleared = 0
    if clear_outputs:
        print("\nClearing outputs for re-execution...")
        outputs_cleared = clear_notebook_outputs(nb)
        print(f"  Cleared outputs from {outputs_cleared} cells")

    # Save modified notebook
    with open(notebook_path, "w") as f:
        json.dump(nb, f, indent=1)

    print(f"\nSummary:")
    print(f"  Files uploaded: {len(url_mapping)}")
    print(f"  Total data size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    print(f"  Cells modified: {cells_modified}")
    print(f"  Path replacements: {total_replacements}")

    return {
        "transformed": cells_modified > 0 or len(url_mapping) > 0,
        "cells_modified": cells_modified,
        "files_uploaded": len(url_mapping),
        "total_size": total_size,
        "outputs_cleared": outputs_cleared,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", help="Path to notebook file")
    parser.add_argument("--working-dir", "-w", help="Working directory for resolving paths")
    parser.add_argument("--clear-outputs", "-c", action="store_true",
                        help="Clear all cell outputs after transform (for two-pass workflow)")

    args = parser.parse_args()

    if not os.path.exists(args.notebook):
        print(f"ERROR: Notebook not found: {args.notebook}")
        sys.exit(1)

    if not DRY_RUN and not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set. Uploads will fail.")

    result = transform_notebook(args.notebook, args.working_dir, clear_outputs=args.clear_outputs)

    if result["transformed"]:
        print(f"\nSuccess! Notebook transformed for HF URLs.")
        if args.clear_outputs:
            print("Outputs cleared - ready for second execution pass.")
    else:
        print(f"\nNo transformation needed: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
