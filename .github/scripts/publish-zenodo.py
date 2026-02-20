#!/usr/bin/env python3
"""Publish a Jupyter notebook to Zenodo, with versioning support.

Exit codes:
    0 - Published successfully (new deposition or new version)
    1 - Error
    2 - Skipped (notebook unchanged, checksum matches)
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from notebook_metadata import extract_authors_from_first_cell


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_source_checksum(notebook_path: str) -> str:
    """MD5 of concatenated source cells only (ignoring outputs/metadata)."""
    with open(notebook_path, "r", encoding="utf-8") as fh:
        nb = json.load(fh)
    sources = []
    for cell in nb.get("cells", []):
        src = cell.get("source", [])
        if isinstance(src, list):
            sources.append("".join(src))
        else:
            sources.append(str(src))
    return hashlib.md5("\n".join(sources).encode("utf-8")).hexdigest()


def api_request(url, *, method="GET", data=None, files=None, token=None,
                headers=None, retries=3, backoff=5):
    """Make an HTTP request to the Zenodo API with retry logic.

    ``files`` should be a tuple (filename, file_bytes, content_type) for a
    single file upload.  When *files* is given, the request is sent as
    multipart/form-data.  Otherwise *data* (bytes) is sent as the body.
    """
    hdrs = {"Authorization": f"Bearer {token}"} if token else {}
    if headers:
        hdrs.update(headers)

    for attempt in range(1, retries + 1):
        try:
            if files:
                fname, fbytes, ctype = files
                boundary = f"----ZenodoBoundary{int(time.time()*1000)}"
                body = bytearray()
                body.extend(f"--{boundary}\r\n".encode())
                body.extend(
                    f'Content-Disposition: form-data; name="file"; '
                    f'filename="{fname}"\r\n'.encode()
                )
                body.extend(f"Content-Type: {ctype}\r\n\r\n".encode())
                body.extend(fbytes)
                body.extend(f"\r\n--{boundary}--\r\n".encode())
                hdrs["Content-Type"] = f"multipart/form-data; boundary={boundary}"
                req = urllib.request.Request(url, data=bytes(body), headers=hdrs,
                                            method=method)
            else:
                if data is not None:
                    hdrs.setdefault("Content-Type", "application/json")
                req = urllib.request.Request(url, data=data, headers=hdrs,
                                            method=method)

            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_body = resp.read()
                if resp_body:
                    return json.loads(resp_body)
                return {}

        except urllib.error.HTTPError as exc:
            status = exc.code
            err_body = exc.read().decode("utf-8", errors="replace")
            if status in (429, 500, 502, 503, 504) and attempt < retries:
                wait = backoff * attempt
                print(f"  Retryable HTTP {status}, waiting {wait}s "
                      f"(attempt {attempt}/{retries})...")
                time.sleep(wait)
                continue
            print(f"HTTP {status}: {err_body}", file=sys.stderr)
            raise
        except urllib.error.URLError as exc:
            if attempt < retries:
                wait = backoff * attempt
                print(f"  Network error: {exc.reason}, waiting {wait}s "
                      f"(attempt {attempt}/{retries})...")
                time.sleep(wait)
                continue
            raise


def delete_draft(api_url, dep_id, token):
    """Best-effort cleanup of a draft deposition."""
    try:
        api_request(f"{api_url}/api/deposit/depositions/{dep_id}",
                    method="DELETE", token=token, retries=1)
        print(f"  Cleaned up draft {dep_id}")
    except Exception:
        print(f"  Warning: could not clean up draft {dep_id}")


# ---------------------------------------------------------------------------
# Core publish logic
# ---------------------------------------------------------------------------

def publish_notebook(notebook_path, notebook_key, doi_mapping_path,
                     output_mapping_path, zenodo_token, api_url):
    """Publish or version a notebook on Zenodo.

    Returns the updated mapping entry dict, or None if skipped.
    """
    # Load existing mapping
    if os.path.isfile(doi_mapping_path):
        with open(doi_mapping_path, "r") as fh:
            mapping = json.load(fh)
    else:
        mapping = {}

    # Compute checksum of source cells
    checksum = compute_source_checksum(notebook_path)
    existing = mapping.get(notebook_key)

    if existing and existing.get("checksum") == checksum:
        print(f"Checksum unchanged for {notebook_key}, skipping.")
        return None  # exit code 2

    notebook_name = os.path.basename(notebook_path).rsplit(".", 1)[0]
    notebook_filename = os.path.basename(notebook_path)
    authors = extract_authors_from_first_cell(notebook_path)
    creators = [{"name": name} for name in authors] if authors else [{"name": "Neurodesk Project"}]

    if authors:
        print(f"Using notebook author metadata: {', '.join(authors)}")
    else:
        print("No author metadata found in first cell, using fallback creator: Neurodesk Project")

    # Read notebook bytes for upload
    with open(notebook_path, "rb") as fh:
        nb_bytes = fh.read()

    # Metadata for the deposition
    title = f"Neurodesk Notebook: {notebook_name}"
    metadata = {
        "metadata": {
            "title": title,
            "upload_type": "lesson",
            "description": (
                f"Executed Jupyter notebook from the Neurodesk education "
                f"platform. Source: {notebook_key}"
            ),
            "creators": creators,
            "license": "MIT",
            "keywords": ["neurodesk", "neuroimaging", "jupyter", "notebook"],
        }
    }

    draft_id = None

    try:
        if existing and existing.get("record_id"):
            # --- New version of existing deposition ---
            record_id = existing["record_id"]
            print(f"Creating new version of record {record_id}...")

            resp = api_request(
                f"{api_url}/api/deposit/depositions/{record_id}/actions/newversion",
                method="POST", token=zenodo_token,
            )

            # The response contains a link to the new draft
            new_draft_url = resp["links"]["latest_draft"]
            draft = api_request(new_draft_url, token=zenodo_token)
            draft_id = draft["id"]
            print(f"  New version draft: {draft_id}")

            # Delete old files from the new draft
            for f in draft.get("files", []):
                api_request(
                    f"{api_url}/api/deposit/depositions/{draft_id}/files/{f['id']}",
                    method="DELETE", token=zenodo_token,
                )
        else:
            # --- Brand new deposition ---
            print(f"Creating new deposition for {notebook_key}...")
            draft = api_request(
                f"{api_url}/api/deposit/depositions",
                method="POST",
                data=json.dumps(metadata).encode(),
                token=zenodo_token,
            )
            draft_id = draft["id"]
            print(f"  New deposition draft: {draft_id}")

        # Upload notebook file
        bucket_url = None
        # Prefer bucket API (newer) over files API
        if "links" in draft and "bucket" in draft["links"]:
            bucket_url = draft["links"]["bucket"]

        if bucket_url:
            print(f"  Uploading {notebook_filename} via bucket API...")
            api_request(
                f"{bucket_url}/{notebook_filename}",
                method="PUT",
                data=nb_bytes,
                headers={"Content-Type": "application/octet-stream"},
                token=zenodo_token,
            )
        else:
            print(f"  Uploading {notebook_filename} via files API...")
            api_request(
                f"{api_url}/api/deposit/depositions/{draft_id}/files",
                method="POST",
                files=(notebook_filename, nb_bytes, "application/octet-stream"),
                token=zenodo_token,
            )

        # Update metadata
        print("  Updating metadata...")
        api_request(
            f"{api_url}/api/deposit/depositions/{draft_id}",
            method="PUT",
            data=json.dumps(metadata).encode(),
            token=zenodo_token,
        )

        # Publish
        print("  Publishing...")
        published = api_request(
            f"{api_url}/api/deposit/depositions/{draft_id}/actions/publish",
            method="POST",
            token=zenodo_token,
        )

        # Extract DOI information
        concept_doi = published.get("conceptdoi", "")
        concept_recid = str(published.get("conceptrecid", ""))
        record_id = str(published["id"])
        doi_url = f"https://doi.org/{concept_doi}" if concept_doi else published.get("links", {}).get("conceptdoi", "")

        print(f"  Published! DOI: {doi_url}")
        print(f"  concept_recid={concept_recid}, record_id={record_id}")

        # Update mapping
        mapping[notebook_key] = {
            "doi_url": doi_url,
            "concept_recid": concept_recid,
            "record_id": record_id,
            "checksum": checksum,
            "authors": authors,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        with open(output_mapping_path, "w") as fh:
            json.dump(mapping, fh, indent=2)
            fh.write("\n")

        return mapping[notebook_key]

    except Exception:
        # Try to clean up the draft on failure
        if draft_id is not None:
            delete_draft(api_url, draft_id, zenodo_token)
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Publish a Jupyter notebook to Zenodo with versioning."
    )
    parser.add_argument("--notebook-path", required=True,
                        help="Path to the executed notebook file")
    parser.add_argument("--notebook-key", required=True,
                        help="Canonical key in doi-mapping.json (e.g. books/examples/...)")
    parser.add_argument("--doi-mapping", required=True,
                        help="Path to doi-mapping.json input")
    parser.add_argument("--output-mapping", required=True,
                        help="Path to write updated doi-mapping.json")
    parser.add_argument("--zenodo-token", required=True,
                        help="Zenodo API token")
    parser.add_argument("--api-url", default="https://zenodo.org",
                        help="Zenodo API base URL (default: https://zenodo.org)")
    args = parser.parse_args()

    try:
        result = publish_notebook(
            notebook_path=args.notebook_path,
            notebook_key=args.notebook_key,
            doi_mapping_path=args.doi_mapping,
            output_mapping_path=args.output_mapping,
            zenodo_token=args.zenodo_token,
            api_url=args.api_url,
        )
        if result is None:
            sys.exit(2)  # Unchanged
        sys.exit(0)  # Published
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
