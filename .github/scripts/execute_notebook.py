#!/usr/bin/env python3
"""Execute a notebook, preserving its partial output if a cell fails."""

import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def execute_notebook(path, *, publication_pass=False, timeout=43200):
    path = Path(path).resolve()
    notebook = nbformat.read(path, as_version=4)
    publication_cells = []
    # Never leave saved source outputs attached to cells that did not run.
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            tags = cell.metadata.get("tags", [])
            if publication_pass and "skip-on-publish" in tags and "skip-execution" not in tags:
                tags.append("skip-execution")
                publication_cells.append(cell)

    client = NotebookClient(
        notebook,
        kernel_name="python3",
        timeout=timeout,
        allow_errors=False,
        force_raise_errors=True,
        resources={"metadata": {"path": str(path.parent)}},
    )
    try:
        client.execute()
    finally:
        for cell in publication_cells:
            cell.metadata.tags.remove("skip-execution")
        # The workflow uploads this notebook for debugging, including on failure.
        nbformat.write(notebook, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--publication-pass", action="store_true")
    parser.add_argument("--timeout", type=int, default=43200)
    args = parser.parse_args()
    execute_notebook(args.notebook, publication_pass=args.publication_pass, timeout=args.timeout)
