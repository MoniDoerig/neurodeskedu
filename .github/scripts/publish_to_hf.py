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
    HF_BRANCH: HuggingFace branch to upload to (default: main)
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
HF_BRANCH = os.environ.get("HF_BRANCH", "main")
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_BRANCH}"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"

_hf_branch_ensured = False


def ensure_hf_branch() -> None:
    """Create the HF branch if it doesn't exist (branching off main)."""
    global _hf_branch_ensured
    if _hf_branch_ensured or DRY_RUN or HF_BRANCH == "main":
        _hf_branch_ensured = True
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi()
        refs = api.list_repo_refs(HF_REPO, repo_type="dataset")
        existing = {b.name for b in refs.branches}
        if HF_BRANCH not in existing:
            print(f"  Creating HF branch '{HF_BRANCH}' from main...")
            api.create_branch(HF_REPO, repo_type="dataset", branch=HF_BRANCH)
        _hf_branch_ensured = True
    except Exception as e:
        print(f"  WARNING: Could not ensure HF branch '{HF_BRANCH}': {e}")


# File extensions that ipyniivue can load
NIIVUE_EXTENSIONS = {
    ".nii.gz", ".nii", ".mgz", ".mgh",  # Volumes
    ".mif",  # MRtrix format
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


def scan_data_files(directory: Path) -> tuple[dict[str, Path], dict[str, list[Path]]]:
    """
    Scan directory recursively for niivue-compatible data files.
    Returns:
        - dict mapping filename -> full path (for unique files)
        - dict mapping filename -> list of paths (for duplicates)
    Excludes common non-data directories.
    """
    # Directories to exclude
    exclude_dirs = {
        ".venv", "venv", ".env", "env",
        "node_modules", ".git", "__pycache__",
        ".cache", ".local", "site-packages",
        "_build", ".ipynb_checkpoints",
    }

    # First pass: collect all files by name
    all_files: dict[str, list[Path]] = {}
    for filepath in directory.rglob("*"):
        # Skip excluded directories
        if any(excluded in filepath.parts for excluded in exclude_dirs):
            continue
        if filepath.is_file() and is_niivue_file(filepath):
            all_files.setdefault(filepath.name, []).append(filepath)

    # Separate unique files from duplicates
    unique_files = {}
    duplicates = {}
    for name, paths in all_files.items():
        if len(paths) == 1:
            unique_files[name] = paths[0]
        else:
            duplicates[name] = paths

    return unique_files, duplicates


def ensure_gitattributes(extensions: set[str]) -> None:
    """Ensure neuroimaging extensions are tracked via LFS/Xet in the HF repo's .gitattributes."""
    if DRY_RUN:
        return

    try:
        from huggingface_hub import hf_hub_download, CommitOperationAdd, HfApi

        ensure_hf_branch()

        # Download current .gitattributes
        try:
            ga_path = hf_hub_download(HF_REPO, ".gitattributes", repo_type="dataset", revision=HF_BRANCH)
            current = open(ga_path).read()
        except Exception:
            current = ""

        # Find extensions not yet covered by wildcard patterns
        missing = []
        for ext in sorted(extensions):
            # Check for wildcard pattern like "*.tck filter=lfs ..."
            pattern = f"*{ext} filter=lfs"
            if pattern not in current:
                missing.append(ext)

        if not missing:
            return

        print(f"  Adding LFS patterns to .gitattributes: {missing}")
        new_lines = "\n".join(
            f"*{ext} filter=lfs diff=lfs merge=lfs -text" for ext in missing
        )
        updated = current.rstrip() + "\n" + new_lines + "\n"

        api = HfApi()
        api.create_commit(
            repo_id=HF_REPO,
            repo_type="dataset",
            revision=HF_BRANCH,
            operations=[CommitOperationAdd(path_in_repo=".gitattributes", path_or_fileobj=updated.encode())],
            commit_message=f"Add LFS patterns for neuroimaging extensions: {', '.join(missing)}",
        )
    except Exception as e:
        print(f"  WARNING: Could not update .gitattributes: {e}")


def upload_to_hf(filepath: Path, path_in_repo: str) -> str:
    """Upload file to Hugging Face and return the URL."""
    url = f"{HF_BASE_URL}/{path_in_repo}"

    if DRY_RUN:
        print(f"  [DRY RUN] Would upload: {filepath} -> {path_in_repo}")
        return url

    try:
        from huggingface_hub import upload_file, file_exists

        ensure_hf_branch()

        if file_exists(HF_REPO, path_in_repo, repo_type="dataset", revision=HF_BRANCH):
            print(f"  Already exists: {path_in_repo}")
            return url

        print(f"  Uploading: {filepath.name} -> {path_in_repo}")

        upload_file(
            path_or_fileobj=str(filepath),
            path_in_repo=path_in_repo,
            repo_id=HF_REPO,
            repo_type="dataset",
            revision=HF_BRANCH,
            commit_message=f"Add data: {path_in_repo}",
        )

        return url

    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install 'huggingface_hub>=0.32.0'")
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


def extract_referenced_files(nb: dict) -> set[str]:
    """
    Extract filenames referenced in ipyniivue calls from notebook cells.
    Returns set of filenames (not full paths).

    Handles multiple patterns:
    - Dict literal: "path": "./data/file.nii.gz"
    - Dict with var: "path": DATA_FOLDER / "file.nii.gz"
    - Kwarg with var: path=DATA_FOLDER / "file.nii.gz"
    - Kwarg literal: path="file.mif"
    - Var assignment: lh = surf_dir / "lh.pial"
    - Fallback: any string containing niivue-compatible extension
    """
    referenced = set()

    # Build regex for niivue extensions (for fallback pattern)
    extensions = [
        r"\.nii\.gz", r"\.nii", r"\.mgz", r"\.mgh",
        r"\.pial", r"\.white", r"\.inflated", r"\.sphere", r"\.surf", r"\.gii",
        r"\.trk", r"\.tck", r"\.vtk", r"\.mz3",
        r"\.HEAD", r"\.BRIK\.gz",
        r"\.tt\.gz", r"\.srf\.gz", r"\.smp\.gz",
        r"\.dtseries\.nii", r"\.dscalar\.nii",
        r"\.mif",
    ]
    ext_pattern = "|".join(extensions)

    # Fallback pattern: any quoted string with a niivue-compatible extension
    # This catches all patterns including path=str(var), var assignments, etc.
    # Require at least one word character before the extension to avoid matching just ".mif"
    pattern_any_niivue_string = rf'["\']([^"\']*\w(?:{ext_pattern}))["\']'

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue

        source = cell.get("source", [])
        if isinstance(source, list):
            source_str = "".join(source)
        else:
            source_str = source

        # Only look in cells with ipyniivue usage
        if not any(kw in source_str for kw in ["load_volumes", "load_meshes", "add_volume", "add_mesh", "NiiVue", "ipyniivue", "Mesh", "Volume"]):
            continue

        # Skip injected patcher cells
        tags = cell.get("metadata", {}).get("tags", [])
        if "hf-url-patcher" in tags:
            continue

        # Use fallback pattern to catch ALL niivue-compatible filenames
        for match in re.finditer(pattern_any_niivue_string, source_str, re.IGNORECASE):
            path_or_filename = match.group(1)
            # Extract just the filename from the path
            filename = Path(path_or_filename).name
            if filename:  # Skip empty filenames
                referenced.add(filename)

    return referenced


PATCHER_TAG = "hf-url-patcher"


def generate_patcher_cell(url_map: dict[str, str]) -> dict:
    """
    Generate a notebook cell that monkey-patches ipyniivue at runtime to replace
    local file paths with HF URLs, keyed by filename.

    Handles: load_volumes, load_meshes, add_volume, add_mesh, Mesh(path=...).
    """
    url_map_repr = repr(url_map)
    source = f'''\
# [HF-URL-PATCHER] Auto-injected by publish_to_hf.py — do not edit
import json as _json
from pathlib import Path as _Path

_HF_URL_MAP = {url_map_repr}


def _resolve_hf(path_val):
    if not path_val:
        return None
    s = str(path_val)
    if s.startswith(("http://", "https://")):
        return None
    try:
        return _HF_URL_MAP.get(_Path(s).name)
    except Exception:
        return None


def _patch_vol_list(vols):
    if not vols:
        return vols
    out = []
    for v in vols:
        if isinstance(v, dict) and "path" in v:
            url = _resolve_hf(v["path"])
            if url:
                v = {{**v, "url": url}}
                del v["path"]
                print(f"[HF-patcher] {{_Path(str(url)).name.split('_')[0]}}: path → url")
        out.append(v)
    return out


try:
    import ipyniivue as _nv_mod

    _orig_lv = _nv_mod.NiiVue.load_volumes
    def _lv(self, volumes, *a, **kw): return _orig_lv(self, _patch_vol_list(volumes), *a, **kw)
    _nv_mod.NiiVue.load_volumes = _lv

    _orig_lm = _nv_mod.NiiVue.load_meshes
    def _lm(self, meshes, *a, **kw): return _orig_lm(self, _patch_vol_list(meshes), *a, **kw)
    _nv_mod.NiiVue.load_meshes = _lm

    _orig_av = _nv_mod.NiiVue.add_volume
    def _av(self, volume, *a, **kw): return _orig_av(self, _patch_vol_list([volume])[0], *a, **kw)
    _nv_mod.NiiVue.add_volume = _av

    _orig_am = _nv_mod.NiiVue.add_mesh
    def _am(self, mesh, *a, **kw): return _orig_am(self, _patch_vol_list([mesh])[0] if isinstance(mesh, dict) else mesh, *a, **kw)
    _nv_mod.NiiVue.add_mesh = _am

    if hasattr(_nv_mod, "Mesh"):
        _orig_mesh = _nv_mod.Mesh.__init__
        def _mesh_init(self, path=None, **kw):
            if path is not None:
                url = _resolve_hf(path)
                if url:
                    print(f"[HF-patcher] {{_Path(str(path)).name}}: path → url")
                    kw["url"] = url
                    path = None
            return _orig_mesh(self, path=path, **kw)
        _nv_mod.Mesh.__init__ = _mesh_init

    print(f"[HF-patcher] ipyniivue patched — {{len(_HF_URL_MAP)}} file(s) mapped to HF URLs")
except Exception as _e:
    print(f"[HF-patcher] Warning: patch failed: {{_e}}")
'''
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": [PATCHER_TAG]},
        "outputs": [],
        "source": source,
    }


def inject_patcher_cell(nb: dict, url_map: dict[str, str]) -> None:
    """Insert the runtime patcher cell at position 0 (before all other cells)."""
    remove_patcher_cells(nb)  # Remove any stale patcher from a previous run
    nb["cells"].insert(0, generate_patcher_cell(url_map))
    print(f"  Injected runtime patcher cell ({len(url_map)} URL mappings)")


def remove_patcher_cells(nb: dict) -> int:
    """Remove all cells tagged as hf-url-patcher. Returns count removed."""
    before = len(nb["cells"])
    nb["cells"] = [
        c for c in nb["cells"]
        if PATCHER_TAG not in c.get("metadata", {}).get("tags", [])
    ]
    removed = before - len(nb["cells"])
    if removed:
        print(f"  Removed {removed} patcher cell(s)")
    return removed


def transform_notebook(notebook_path: str, working_dir: str = None, clear_outputs: bool = False) -> dict:
    """
    Transform notebook: find referenced files, upload to HF, rewrite paths to URLs.
    Only uploads files that are actually used in ipyniivue calls.
    """
    notebook_path = Path(notebook_path)

    if working_dir:
        working_dir = Path(working_dir)
    else:
        working_dir = notebook_path.parent

    print(f"\nProcessing: {notebook_path}")
    print(f"Working dir: {working_dir}")
    print(f"HF branch: {HF_BRANCH}")

    # Load notebook
    with open(notebook_path) as f:
        nb = json.load(f)

    # Determine HF path prefix for data files
    # Data goes under data/examples/modality/notebook_name/
    notebook_rel = str(notebook_path.with_suffix(""))
    if notebook_rel.startswith("books/"):
        notebook_rel = notebook_rel[6:]
    notebook_hf_prefix = f"data/{notebook_rel}"

    print(f"HF prefix: {notebook_hf_prefix}")

    # First: extract filenames actually referenced in ipyniivue calls
    print("\nExtracting referenced files from notebook...")
    referenced_files = extract_referenced_files(nb)
    print(f"  Found {len(referenced_files)} referenced files: {sorted(referenced_files)}")

    # Scan working directory for all niivue files
    print("\nScanning for niivue data files...")
    unique_files, duplicates = scan_data_files(working_dir)
    print(f"  Found {len(unique_files)} unique files, {len(duplicates)} with duplicates")

    # Decide mode: static rewriting vs runtime patcher
    # Static rewriting requires knowing the exact filenames from source code.
    # Patcher mode handles dynamic paths (glob, tempfile, f-strings, variables).
    use_patcher = False

    if not referenced_files:
        # No static filenames detected — dynamic paths (glob, tempfile, variables).
        # Fall back to uploading all NII files and using the runtime patcher.
        print("  No static file references detected — using runtime patcher fallback")
        use_patcher = True
        data_files = dict(unique_files)
        # Resolve duplicates: use identical copies, error on divergent ones
        for name, paths in duplicates.items():
            hashes = {get_file_hash(p): p for p in paths}
            if len(hashes) == 1:
                data_files[name] = paths[0]
            else:
                print(f"\nERROR: {name} has {len(paths)} copies with DIFFERENT content — cannot resolve")
                for p in paths:
                    print(f"    - {p}  (hash: {get_file_hash(p)})")
                sys.exit(1)
    else:
        # Handle duplicates in referenced files via hash check
        referenced_duplicates = {name: paths for name, paths in duplicates.items() if name in referenced_files}
        if referenced_duplicates:
            for name, paths in referenced_duplicates.items():
                hashes = {get_file_hash(p): p for p in paths}
                if len(hashes) == 1:
                    print(f"  {name}: {len(paths)} copies found, all identical (hash match) — using first")
                    unique_files[name] = paths[0]
                else:
                    print("\n" + "=" * 60)
                    print(f"ERROR: {name} has {len(paths)} copies with DIFFERENT content!")
                    print("Cannot determine which file the notebook is using.")
                    print("=" * 60)
                    for p in paths:
                        print(f"    - {p}  (hash: {get_file_hash(p)})")
                    print()
                    sys.exit(1)

        # Filter to only files that are actually referenced
        data_files = {name: path for name, path in unique_files.items() if name in referenced_files}
        print(f"  {len(data_files)} files match references")

        # Warn about missing files
        missing = referenced_files - set(data_files.keys())
        if missing:
            print(f"  WARNING: {len(missing)} referenced files not found: {sorted(missing)}")

        if not data_files:
            print("  No matching data files found")
            return {"transformed": False, "reason": "no_matching_files"}

    if not data_files:
        print("  No NII files found in working directory — cannot transform")
        return {"transformed": False, "reason": "no_files_found"}

    # Upload files to HuggingFace
    print("\nUploading to Hugging Face...")

    # Ensure .gitattributes has LFS patterns for all our file extensions
    data_extensions = {filepath.suffix.lower() for filepath in data_files.values()}
    # Also add compound extensions
    for name in data_files:
        name_lower = name.lower()
        for ext in COMPOUND_EXTENSIONS:
            if name_lower.endswith(ext.lower()):
                data_extensions.add(ext.lower())
    ensure_gitattributes(data_extensions)

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

    cells_modified = 0
    total_replacements = 0

    if use_patcher:
        # Inject runtime patcher cell — handles dynamic paths at execution time
        print("\nInjecting runtime patcher cell...")
        inject_patcher_cell(nb, url_mapping)
        cells_modified = 1  # The injected cell counts as a modification
    else:
        # Static rewriting: replace literal path strings with HF URLs in source
        print("\nTransforming notebook cells...")
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

        if cells_modified == 0 and url_mapping:
            # Files were found and uploaded but static rewriting matched nothing
            # (e.g. paths built via variables). Fall back to patcher.
            print("  Static rewriting matched no cells — falling back to runtime patcher")
            inject_patcher_cell(nb, url_mapping)
            use_patcher = True
            cells_modified = 1

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
    print(f"  Mode: {'runtime patcher' if use_patcher else 'static rewriting'}")
    print(f"  Files uploaded: {len(url_mapping)}")
    print(f"  Total data size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    print(f"  Cells modified: {cells_modified}")
    if not use_patcher:
        print(f"  Path replacements: {total_replacements}")

    return {
        "transformed": cells_modified > 0 or len(url_mapping) > 0,
        "cells_modified": cells_modified,
        "files_uploaded": len(url_mapping),
        "total_size": total_size,
        "outputs_cleared": outputs_cleared,
        "used_patcher": use_patcher,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", help="Path to notebook file")
    parser.add_argument("--working-dir", "-w", help="Working directory for resolving paths")
    parser.add_argument("--clear-outputs", "-c", action="store_true",
                        help="Clear all cell outputs after transform (for two-pass workflow)")
    parser.add_argument("--remove-patcher", action="store_true",
                        help="Remove injected patcher cell(s) and save — run after second execution")

    args = parser.parse_args()

    if not os.path.exists(args.notebook):
        print(f"ERROR: Notebook not found: {args.notebook}")
        sys.exit(1)

    if args.remove_patcher:
        with open(args.notebook) as f:
            nb = json.load(f)
        removed = remove_patcher_cells(nb)
        with open(args.notebook, "w") as f:
            json.dump(nb, f, indent=1)
        print(f"Removed {removed} patcher cell(s) from {args.notebook}")
        return

    if not DRY_RUN and not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set. Uploads will fail.")

    result = transform_notebook(args.notebook, args.working_dir, clear_outputs=args.clear_outputs)

    if result["transformed"]:
        mode = "runtime patcher" if result.get("used_patcher") else "static rewriting"
        print(f"\nSuccess! Notebook transformed for HF URLs ({mode}).")
        if args.clear_outputs:
            print("Outputs cleared - ready for second execution pass.")
    else:
        print(f"\nNo transformation needed: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
