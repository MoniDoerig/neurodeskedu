#!/usr/bin/env python3
"""
Publish large embedded widget data to Hugging Face.

This script:
1. Extracts large embedded data from Jupyter widget state (e.g., ipyniivue volumes)
2. Uploads the data to a Hugging Face dataset
3. Modifies the notebook to reference HF URLs instead of embedded data

This keeps notebook/HTML files small while preserving interactive widgets.

Usage:
    python publish_to_hf.py <notebook.ipynb>

Environment variables:
    HF_TOKEN: Hugging Face token with write access (required for upload)
    HF_REPO: Hugging Face dataset repo (default: neurodeskorg/neurodeskedu)
    DRY_RUN: If set to "true", skip upload and just report what would be done
"""

import json
import base64
import os
import sys
import hashlib
from pathlib import Path

# Hugging Face configuration
HF_REPO = os.environ.get("HF_REPO", "neurodeskorg/neurodeskedu")
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"


def get_content_hash(data: bytes) -> str:
    """Generate a short hash of the content for deduplication."""
    return hashlib.sha256(data).hexdigest()[:12]


def upload_to_hf(data: bytes, path_in_repo: str) -> str:
    """Upload data to Hugging Face and return the URL."""
    url = f"{HF_BASE_URL}/{path_in_repo}"

    if DRY_RUN:
        print(f"  [DRY RUN] Would upload to: {path_in_repo}")
        return url

    try:
        from huggingface_hub import upload_file, hf_hub_url, file_exists
        from io import BytesIO

        # Check if file already exists (skip upload if so)
        if file_exists(HF_REPO, path_in_repo, repo_type="dataset"):
            print(f"  Already exists on HF: {path_in_repo} (skipping upload)")
            return url

        print(f"  Uploading to HF: {path_in_repo} ({len(data):,} bytes)...")

        upload_file(
            path_or_fileobj=BytesIO(data),
            path_in_repo=path_in_repo,
            repo_id=HF_REPO,
            repo_type="dataset",
            commit_message=f"Add volume data: {path_in_repo}",
        )

        print(f"  Uploaded: {url}")
        return url

    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR uploading to HF: {e}")
        raise


def transform_notebook(notebook_path: str) -> dict:
    """
    Transform notebook to use HF URLs instead of embedded volume data.

    Returns dict with transformation results.
    """
    notebook_path = Path(notebook_path)
    print(f"\nProcessing: {notebook_path}")

    # Load notebook
    with open(notebook_path) as f:
        nb = json.load(f)

    # Check for widget state
    if "widgets" not in nb.get("metadata", {}):
        print("  No widget state found - skipping")
        return {"transformed": False, "reason": "no_widgets"}

    widgets = nb["metadata"]["widgets"].get("application/vnd.jupyter.widget-state+json", {})
    state = widgets.get("state", {})

    if not state:
        print("  Empty widget state - skipping")
        return {"transformed": False, "reason": "empty_state"}

    # Use relative path (without extension) to prevent collisions between
    # notebooks with the same name in different directories
    # e.g., "books/examples/structural_imaging/intro.ipynb" -> "examples/structural_imaging/intro"
    notebook_rel_path = str(notebook_path.with_suffix(""))
    if notebook_rel_path.startswith("books/"):
        notebook_rel_path = notebook_rel_path[6:]  # Remove "books/" prefix

    original_size = notebook_path.stat().st_size
    uploaded_files = []
    models_transformed = 0

    # Process each widget model
    for model_id, model in state.items():
        if "buffers" not in model or len(model["buffers"]) == 0:
            continue

        model_state = model.get("state", {})

        # Get volume name for filename
        volume_name = model_state.get("name", "volume")
        # Sanitize name for filename
        volume_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in volume_name)

        print(f"\n  Model {model_id[:8]}... (volume: {volume_name})")

        # Process each buffer
        for i, buf in enumerate(model["buffers"]):
            if not isinstance(buf, dict) or "data" not in buf:
                continue

            encoding = buf.get("encoding", "base64")
            data = buf["data"]

            print(f"    Buffer {i}: {len(data):,} chars ({encoding})")

            # Decode data
            if encoding == "base64":
                try:
                    volume_bytes = base64.b64decode(data)
                except Exception as e:
                    print(f"    WARNING: Failed to decode base64: {e}")
                    continue
            else:
                print(f"    WARNING: Unknown encoding {encoding}, skipping")
                continue

            # Skip small buffers (not worth uploading to HF)
            MIN_UPLOAD_SIZE = 1 * 1024 * 1024  # 1MB
            if len(volume_bytes) < MIN_UPLOAD_SIZE:
                print(f"    Skipping (below 1MB threshold: {len(volume_bytes):,} bytes)")
                continue

            # Generate filename with content hash for deduplication
            content_hash = get_content_hash(volume_bytes)
            output_filename = f"{volume_name}_{content_hash}.nii.gz"
            hf_path = f"{notebook_rel_path}/{output_filename}"

            print(f"    Decoded: {len(volume_bytes):,} bytes")

            # Upload to HF
            hf_url = upload_to_hf(volume_bytes, hf_path)

            uploaded_files.append({
                "hf_path": hf_path,
                "hf_url": hf_url,
                "size_bytes": len(volume_bytes),
                "model_id": model_id,
            })

            # Set URL in widget state (ipyniivue requires only one of: path, url, data)
            model_state["url"] = hf_url

            # Clear competing fields - ipyniivue will use url instead
            # (ipyniivue requires only one of: path, url, data)
            for field in ["path", "data", "img", "buffer_src"]:
                if field in model_state and model_state[field]:
                    print(f"    Clearing {field}")
                    model_state[field] = None

            print(f"    Set URL: {hf_url}")

        # Clear the buffers (remove embedded binary data)
        original_buffer_size = sum(len(json.dumps(b)) for b in model["buffers"])
        model["buffers"] = []
        models_transformed += 1
        print(f"    Cleared buffers ({original_buffer_size:,} chars)")

    if models_transformed == 0:
        print("  No buffers to transform - skipping")
        return {"transformed": False, "reason": "no_buffers"}

    # Save modified notebook (overwrite original)
    with open(notebook_path, "w") as f:
        json.dump(nb, f, indent=1)

    modified_size = notebook_path.stat().st_size
    size_reduction = original_size - modified_size

    print(f"\n  Summary:")
    print(f"    Original size: {original_size:,} bytes ({original_size/1024/1024:.2f} MB)")
    print(f"    Modified size: {modified_size:,} bytes ({modified_size/1024/1024:.2f} MB)")
    print(f"    Size reduction: {size_reduction:,} bytes ({size_reduction/1024/1024:.2f} MB)")
    print(f"    Models transformed: {models_transformed}")
    print(f"    Files uploaded: {len(uploaded_files)}")

    return {
        "transformed": True,
        "original_size": original_size,
        "modified_size": modified_size,
        "size_reduction": size_reduction,
        "models_transformed": models_transformed,
        "uploaded_files": uploaded_files,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    notebook_path = sys.argv[1]

    if not os.path.exists(notebook_path):
        print(f"ERROR: Notebook not found: {notebook_path}")
        sys.exit(1)

    # Check for HF token
    if not DRY_RUN and not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN not set. Upload will fail without authentication.")
        print("Set HF_TOKEN environment variable or use DRY_RUN=true to test.")

    result = transform_notebook(notebook_path)

    if result["transformed"]:
        print(f"\nSuccess! Notebook transformed and volumes uploaded to HF.")
        sys.exit(0)
    else:
        print(f"\nNo transformation needed: {result.get('reason', 'unknown')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
