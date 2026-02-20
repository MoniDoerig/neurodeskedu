#!/usr/bin/env python3
"""Helpers to extract metadata from the first notebook cell."""

from __future__ import annotations

import json
import re
from typing import List


_AUTHOR_LINE_RE = re.compile(r"^authors?\s*:?[\s\-]*(.*)$", re.IGNORECASE)
_STOP_LINE_RE = re.compile(
    r"^(date|title|license|doi|institution|affiliation|contact|email|version)\b",
    re.IGNORECASE,
)


def _strip_markdown(text: str) -> str:
    """Collapse simple markdown formatting to plain text."""
    cleaned = text.strip()
    cleaned = re.sub(r"\[(.*?)\]\([^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"</?[^>]+>", " ", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"^\s*[-+>#]+\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _looks_like_person(token: str) -> bool:
    words = [word for word in token.split() if word]
    if len(words) < 2:
        return False
    if not any(ch.isalpha() for ch in token):
        return False
    if token.upper() == token and len(token) <= 6:
        return False
    return True


def _split_authors(raw_value: str) -> List[str]:
    """Split a raw author string into a list of names."""
    value = _strip_markdown(raw_value)
    value = re.sub(r"\s+and\s+", " & ", value, flags=re.IGNORECASE)

    if "&" in value:
        candidates = [part.strip() for part in value.split("&")]
    elif ";" in value:
        candidates = [part.strip() for part in value.split(";")]
    elif "," in value and "(" not in value and ")" not in value:
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if len(parts) >= 2 and all(_looks_like_person(part) for part in parts):
            candidates = parts
        else:
            candidates = [value]
    else:
        candidates = [value]

    deduped: List[str] = []
    for candidate in candidates:
        normalized = _strip_markdown(candidate)
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def extract_authors_from_first_cell_source(first_cell_source: str) -> List[str]:
    """Extract author names from the first notebook cell text."""
    lines = first_cell_source.splitlines()
    for index, line in enumerate(lines):
        cleaned_line = _strip_markdown(line)
        match = _AUTHOR_LINE_RE.match(cleaned_line)
        if not match:
            continue

        inline_value = match.group(1).strip()
        if inline_value:
            return _split_authors(inline_value)

        continuation: List[str] = []
        for next_line in lines[index + 1 :]:
            raw_next = next_line.strip()
            cleaned_next = _strip_markdown(next_line)

            if not cleaned_next:
                if continuation:
                    break
                continue
            if _STOP_LINE_RE.match(cleaned_next):
                break
            if raw_next.startswith("#"):
                break
            if _AUTHOR_LINE_RE.match(cleaned_next):
                break

            continuation.append(cleaned_next)

        if continuation:
            return _split_authors(" ".join(continuation))
        return []

    return []


def extract_authors_from_notebook(notebook_obj: dict) -> List[str]:
    """Extract author names from the first notebook cell."""
    first_cell_source = ""
    cells = notebook_obj.get("cells", [])
    if cells:
        source = cells[0].get("source", [])
        first_cell_source = "".join(source) if isinstance(source, list) else str(source)
    return extract_authors_from_first_cell_source(first_cell_source)


def extract_authors_from_first_cell(notebook_path: str) -> List[str]:
    """Load a notebook and return author names from the first cell."""
    with open(notebook_path, "r", encoding="utf-8") as fh:
        notebook_obj = json.load(fh)
    return extract_authors_from_notebook(notebook_obj)
