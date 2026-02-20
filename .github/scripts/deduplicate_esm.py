#!/usr/bin/env python3
"""
Deduplicate _esm fields in Jupyter widget state within HTML files.

ipyniivue widgets embed ~5MB of JavaScript per widget instance. When a notebook
has multiple widgets, this duplicates the same code many times.

This script:
1. Parses HTML files with embedded widget state
2. Identifies duplicate _esm content by hash
3. Stores unique _esm values once in a lookup table
4. Replaces duplicates with small reference markers
5. Injects JavaScript that resolves references at runtime

Usage:
    python deduplicate_esm.py <file.html> [<file2.html> ...]
    python deduplicate_esm.py --dir <directory>
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def extract_widget_state(html_content: str) -> tuple[str | None, int, int]:
    """
    Extract widget state JSON from HTML.
    Returns (json_string, start_pos, end_pos) or (None, -1, -1) if not found.
    """
    pattern = r'(<script type="application/vnd\.jupyter\.widget-state\+json">)\s*(\{.*?\})\s*(</script>)'
    match = re.search(pattern, html_content, re.DOTALL)
    if match:
        return match.group(2), match.start(2), match.end(2)
    return None, -1, -1


def deduplicate_esm(widget_state: dict) -> tuple[dict, dict, int]:
    """
    Deduplicate _esm fields in widget state.

    Returns:
        - Modified widget state with _esm replaced by references
        - Lookup table mapping hash -> original _esm content
        - Number of bytes saved
    """
    state = widget_state.get("state", {})
    esm_lookup = {}  # hash -> esm content
    bytes_saved = 0

    for model_id, model_data in state.items():
        model_state = model_data.get("state", {})

        if "_esm" not in model_state:
            continue

        esm = model_state["_esm"]
        if not isinstance(esm, str) or len(esm) < 1000:
            # Skip small _esm (like 430 byte ones) - not worth deduplicating
            continue

        esm_hash = hashlib.sha256(esm.encode()).hexdigest()[:16]

        if esm_hash not in esm_lookup:
            # First occurrence - store in lookup
            esm_lookup[esm_hash] = esm
        else:
            # Duplicate - count savings
            bytes_saved += len(esm)

        # Replace with reference marker
        model_state["_esm"] = f"__ESM_REF__:{esm_hash}"

    return widget_state, esm_lookup, bytes_saved


def create_esm_resolver_script(esm_lookup: dict) -> str:
    """
    Create JavaScript that resolves _esm references at runtime.

    This script:
    1. Stores the deduplicated _esm content in a lookup table
    2. Patches the Jupyter widget manager to resolve __ESM_REF__ markers
    """
    # Escape the ESM content for JavaScript string literal
    lookup_entries = []
    for hash_id, esm_content in esm_lookup.items():
        # Use JSON.stringify approach to safely escape the content
        escaped = json.dumps(esm_content)
        lookup_entries.append(f'"{hash_id}": {escaped}')

    lookup_js = "{" + ",\n".join(lookup_entries) + "}"

    return f'''<script>
(function() {{
  // Deduplicated ESM lookup table
  const ESM_LOOKUP = {lookup_js};

  // Patch widget state before manager processes it
  const originalParse = JSON.parse;
  let patched = false;

  JSON.parse = function(text) {{
    const result = originalParse.apply(this, arguments);

    // Only patch widget state objects
    if (result && result.state && !patched) {{
      for (const [modelId, modelData] of Object.entries(result.state)) {{
        if (modelData.state && modelData.state._esm) {{
          const esm = modelData.state._esm;
          if (typeof esm === 'string' && esm.startsWith('__ESM_REF__:')) {{
            const hash = esm.slice(12);
            if (ESM_LOOKUP[hash]) {{
              modelData.state._esm = ESM_LOOKUP[hash];
            }}
          }}
        }}
      }}
      patched = true;
    }}
    return result;
  }};
}})();
</script>'''


def process_html_file(filepath: Path, dry_run: bool = False) -> dict:
    """
    Process a single HTML file to deduplicate _esm fields.

    Returns dict with processing statistics.
    """
    result = {
        "file": str(filepath),
        "original_size": 0,
        "new_size": 0,
        "esm_count": 0,
        "unique_esm": 0,
        "bytes_saved": 0,
        "modified": False,
    }

    content = filepath.read_text(encoding="utf-8")
    result["original_size"] = len(content)

    # Extract widget state
    widget_json, start_pos, end_pos = extract_widget_state(content)
    if not widget_json:
        print(f"  No widget state found in {filepath.name}")
        return result

    try:
        widget_state = json.loads(widget_json)
    except json.JSONDecodeError as e:
        print(f"  Failed to parse widget state in {filepath.name}: {e}")
        return result

    # Count _esm fields
    state = widget_state.get("state", {})
    esm_fields = []
    for model_id, model_data in state.items():
        model_state = model_data.get("state", {})
        if "_esm" in model_state and isinstance(model_state["_esm"], str):
            esm_fields.append((model_id, len(model_state["_esm"])))

    result["esm_count"] = len(esm_fields)

    if not esm_fields:
        print(f"  No _esm fields found in {filepath.name}")
        return result

    # Deduplicate
    modified_state, esm_lookup, bytes_saved = deduplicate_esm(widget_state)
    result["unique_esm"] = len(esm_lookup)
    result["bytes_saved"] = bytes_saved

    if bytes_saved == 0:
        print(f"  No duplicate _esm in {filepath.name}")
        return result

    # Create resolver script
    resolver_script = create_esm_resolver_script(esm_lookup)

    # Build new content
    new_widget_json = json.dumps(modified_state, separators=(",", ":"))

    # Replace widget state in HTML
    new_content = content[:start_pos] + new_widget_json + content[end_pos:]

    # Inject resolver script before the widget state script
    widget_script_start = new_content.find('<script type="application/vnd.jupyter.widget-state+json">')
    if widget_script_start > 0:
        new_content = new_content[:widget_script_start] + resolver_script + "\n" + new_content[widget_script_start:]

    result["new_size"] = len(new_content)
    result["modified"] = True

    if dry_run:
        print(f"  [DRY RUN] Would save {bytes_saved:,} bytes in {filepath.name}")
    else:
        filepath.write_text(new_content, encoding="utf-8")
        print(f"  Saved {bytes_saved:,} bytes ({bytes_saved/1024/1024:.2f} MB) in {filepath.name}")

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="HTML files to process")
    parser.add_argument("--dir", "-d", help="Directory to search for HTML files")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    files = []

    if args.dir:
        dir_path = Path(args.dir)
        files.extend(dir_path.glob("**/*.html"))

    if args.files:
        files.extend(Path(f) for f in args.files)

    if not files:
        print("No files specified. Use --dir <directory> or provide file paths.")
        sys.exit(1)

    print(f"Processing {len(files)} HTML file(s)...")

    total_saved = 0
    modified_count = 0

    for filepath in files:
        if not filepath.exists():
            print(f"  File not found: {filepath}")
            continue

        result = process_html_file(filepath, dry_run=args.dry_run)

        if result["modified"]:
            total_saved += result["bytes_saved"]
            modified_count += 1

    print(f"\nSummary:")
    print(f"  Files modified: {modified_count}")
    print(f"  Total bytes saved: {total_saved:,} ({total_saved/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
