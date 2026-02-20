#!/usr/bin/env python3
"""
Deduplicate _esm fields in Jupyter widget state (hash-based, safe).

ipyniivue/anywidget embeds the full JavaScript module (~5MB) in each widget's _esm field.
With multiple widgets, this bloats notebooks to 20-30MB.

This script:
1. Groups _esm fields by content hash
2. Only deduplicates when hashes match (safe - identical content)
3. Keeps one copy per unique hash, replaces others with reference markers
4. Injects restoration script to copy _esm at page load

Usage:
    python deduplicate_esm.py <notebook.ipynb>
"""

import json
import sys
from pathlib import Path
from hashlib import sha256


def deduplicate_esm(notebook_path: str) -> dict:
    """
    Deduplicate _esm fields in notebook widget state.
    Only deduplicates when content hashes match (safe).
    """
    notebook_path = Path(notebook_path)

    with open(notebook_path) as f:
        nb = json.load(f)

    widgets_meta = nb.get("metadata", {}).get("widgets", {})
    widget_state = widgets_meta.get("application/vnd.jupyter.widget-state+json", {})
    state = widget_state.get("state", {})

    if not state:
        print("No widget state found")
        return {"deduplicated": False, "reason": "no_widgets"}

    # Group _esm fields by content hash
    esm_by_hash = {}  # hash -> [(model_id, content, size), ...]

    for model_id, model in state.items():
        esm = model.get("state", {}).get("_esm", "")
        if esm and len(esm) > 1000:  # Only significant _esm fields
            content_hash = sha256(esm.encode()).hexdigest()[:16]
            if content_hash not in esm_by_hash:
                esm_by_hash[content_hash] = []
            esm_by_hash[content_hash].append((model_id, esm, len(esm)))

    if not esm_by_hash:
        print("No significant _esm fields found")
        return {"deduplicated": False, "reason": "no_esm"}

    # Only process groups with duplicates (hash matches)
    duplicate_groups = {h: w for h, w in esm_by_hash.items() if len(w) > 1}

    if not duplicate_groups:
        print("No duplicate _esm fields found (all hashes unique)")
        return {"deduplicated": False, "reason": "no_duplicates"}

    total_widgets = sum(len(v) for v in esm_by_hash.values())
    total_duplicates = sum(len(w) - 1 for w in duplicate_groups.values())

    print(f"Found {len(esm_by_hash)} unique _esm hashes across {total_widgets} widgets")
    print(f"Duplicate groups: {len(duplicate_groups)} (will deduplicate {total_duplicates} widgets)")

    # Deduplicate: keep first per hash, replace others with reference
    saved_bytes = 0
    references = {}

    for content_hash, widgets in duplicate_groups.items():
        # Sort for consistency, keep first
        widgets.sort(key=lambda x: x[0])
        keeper_id, keeper_content, keeper_size = widgets[0]

        print(f"\n  Hash {content_hash}:")
        print(f"    Keeping: {keeper_id[:16]}... ({keeper_size:,} bytes)")

        for dup_id, _, dup_size in widgets[1:]:
            ref_marker = f"__ESM_DEDUP_REF__:{keeper_id}"
            state[dup_id]["state"]["_esm"] = ref_marker
            references[dup_id] = keeper_id
            saved_bytes += dup_size - len(ref_marker)
            print(f"    Deduped: {dup_id[:16]}... (saved {dup_size:,} bytes)")

    # Restoration script - runs at page load to copy _esm from keeper to references
    restoration_script = """
<script type="text/javascript">
(function() {
    function restoreEsmRefs() {
        var scripts = document.querySelectorAll('script[type="application/vnd.jupyter.widget-state+json"]');
        scripts.forEach(function(script) {
            try {
                var data = JSON.parse(script.textContent);
                var state = data.state || data;
                var modified = false;
                for (var id in state) {
                    var widgetState = state[id].state;
                    if (widgetState && widgetState._esm &&
                        typeof widgetState._esm === 'string' &&
                        widgetState._esm.startsWith('__ESM_DEDUP_REF__:')) {
                        var refId = widgetState._esm.split(':')[1];
                        var refState = state[refId] && state[refId].state;
                        if (refState && refState._esm && !refState._esm.startsWith('__ESM_DEDUP_REF__:')) {
                            widgetState._esm = refState._esm;
                            modified = true;
                        }
                    }
                }
                if (modified) {
                    script.textContent = JSON.stringify(data);
                }
            } catch(e) { console.warn('ESM dedup restoration:', e); }
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', restoreEsmRefs);
    } else {
        restoreEsmRefs();
    }
})();
</script>
""".strip()

    # Store restoration info in metadata
    widget_state["_esm_dedup"] = {
        "version": 1,
        "references": references,
        "script": restoration_script,
    }

    # Save modified notebook
    with open(notebook_path, "w") as f:
        json.dump(nb, f, indent=1)

    original_size = sum(size for widgets in esm_by_hash.values() for _, _, size in widgets)
    final_size = original_size - saved_bytes

    print(f"\nDeduplication complete:")
    print(f"  Original: {original_size:,} bytes ({original_size/1024/1024:.2f} MB)")
    print(f"  Saved: {saved_bytes:,} bytes ({saved_bytes/1024/1024:.2f} MB)")
    print(f"  Final: {final_size:,} bytes ({final_size/1024/1024:.2f} MB)")
    print(f"  Reduction: {saved_bytes/original_size*100:.1f}%")

    return {
        "deduplicated": True,
        "original_bytes": original_size,
        "saved_bytes": saved_bytes,
        "duplicates_removed": total_duplicates,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python deduplicate_esm.py <notebook.ipynb>")
        sys.exit(1)

    notebook_path = sys.argv[1]
    if not Path(notebook_path).exists():
        print(f"ERROR: Notebook not found: {notebook_path}")
        sys.exit(1)

    result = deduplicate_esm(notebook_path)

    if result["deduplicated"]:
        print(f"\nSuccess! Reduced by {result['saved_bytes']/1024/1024:.2f} MB")
    else:
        print(f"\nNo deduplication needed: {result.get('reason', 'unknown')}")


if __name__ == "__main__":
    main()
