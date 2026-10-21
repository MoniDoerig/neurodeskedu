#!/usr/bin/env python3
"""Reuse execution results without replacing current tutorial source with a cache."""

import argparse
import copy
import json
from pathlib import Path


def merge_outputs(source: dict, executed: dict) -> bool:
    current = [cell for cell in source["cells"] if cell["cell_type"] == "code"]
    cached = [cell for cell in executed["cells"] if cell["cell_type"] == "code"]
    # A change anywhere in the code can invalidate later outputs and widget state.
    if not current or ["".join(c["source"]) for c in current] != ["".join(c["source"]) for c in cached]:
        return False
    for cell, result in zip(current, cached):
        cell["outputs"] = copy.deepcopy(result.get("outputs", []))
        cell["execution_count"] = result.get("execution_count")
    metadata = source.setdefault("metadata", {})
    if "widgets" in executed.get("metadata", {}):
        metadata["widgets"] = copy.deepcopy(executed["metadata"]["widgets"])
    else:
        metadata.pop("widgets", None)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("executed", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    if merge_outputs(source, json.loads(args.executed.read_text())):
        args.source.write_text(json.dumps(source, ensure_ascii=False, indent=1) + "\n")
        print(f"Reused matching code outputs: {args.source}")
    else:
        print(f"Kept current notebook (cached code differs or is empty): {args.source}")


if __name__ == "__main__":
    main()
