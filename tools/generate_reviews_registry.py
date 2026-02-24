"""Generate NeurodeskEDU review registry JSON.

Converts GitHub Issues+Labels in the reviews repo into a single registry
file (reviews.json) consumed by the badge JS on the built site.

Each review issue contains an HTML comment block with a stable review_id
(UUID). This same ID is embedded in the notebook/page source so the badge
JS can match the current page to a registry entry without relying on
file paths.

Issue body convention:
  <!-- nd-review
  review_id: 550e8400-e29b-41d4-a716-446655440000
  doi_url: https://doi.org/...
  review_commit_sha: <sha>
  reviewed_at: 2026-02-12
  reviewers: reviewer-a, reviewer-b
  -->

Labels -> state mapping:
  reviewed           => reviewed
  review:accepted    => reviewed
  review:in-progress => in-progress
  review:queued      => queued
  review:stale       => stale

Precedence when multiple labels exist:
  stale > reviewed > in-progress > queued > unreviewed
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_PRECEDENCE = ["stale", "reviewed", "in-progress", "queued", "unreviewed"]

LABEL_TO_STATE: Dict[str, str] = {
    "reviewed": "reviewed",
    "review:accepted": "reviewed",
    "review:in-progress": "in-progress",
    "review:in progress": "in-progress",
    "review:queued": "queued",
    "review:stale": "stale",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _http_get_json(url: str, token: Optional[str] = None) -> Any:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "neurodeskedu-reviews-registry-generator")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_nd_review_block(body: str) -> Dict[str, str]:
    """Parse the <!-- nd-review ... --> HTML comment block."""
    if not body:
        return {}
    m = re.search(r"<!--\s*nd-review\s*(.*?)\s*-->", body, re.DOTALL | re.IGNORECASE)
    if not m:
        return {}
    out: Dict[str, str] = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def _infer_state(labels: List[str]) -> str:
    mapped = set()
    for label in labels:
        s = LABEL_TO_STATE.get(label.strip().lower())
        if s:
            mapped.add(s)
    for state in STATE_PRECEDENCE:
        if state in mapped:
            return state
    return "unreviewed"


def _labels_from_issue(issue: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for l in issue.get("labels") or []:
        if isinstance(l, dict) and "name" in l:
            out.append(str(l["name"]))
        elif isinstance(l, str):
            out.append(l)
    return out


def _reviewers_from_issue(issue: Dict[str, Any], nd: Dict[str, str]) -> List[str]:
    """Return reviewer GitHub handles, preferring the nd-review block."""
    raw = nd.get("reviewers")
    if raw:
        reviewers: List[str] = []
        for r in re.split(r"[\s,]+", raw.strip()):
            r = r.strip().lstrip("@")
            if r:
                reviewers.append(r)
        return reviewers
    # Fallback: issue assignees
    out: List[str] = []
    for a in issue.get("assignees") or []:
        login = a.get("login") if isinstance(a, dict) else None
        if login:
            out.append(str(login))
    return out


# ---------------------------------------------------------------------------
# Issue -> registry entry
# ---------------------------------------------------------------------------

def _issue_to_entry(issue: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """Extract a single registry entry from a GitHub issue.

    Returns (review_id, entry_dict).  review_id is None if the issue
    doesn't contain a valid nd-review block with a review_id.
    """
    nd = _extract_nd_review_block(issue.get("body") or "")

    review_id = nd.get("review_id")
    if not review_id:
        return None, {}

    labels = _labels_from_issue(issue)
    state = _infer_state(labels)
    reviewers = _reviewers_from_issue(issue, nd)

    entry: Dict[str, Any] = {
        "state": state,
        "review_issue_url": issue.get("html_url"),
    }

    # Optional fields — only include when present
    for key in ("doi_url", "doi"):
        if nd.get(key):
            entry["doi_url"] = nd[key]
            break
    if reviewers:
        entry["reviewers"] = reviewers
    if nd.get("reviewed_at"):
        entry["reviewed_at"] = nd["reviewed_at"]
    for key in ("review_commit_sha", "review_sha"):
        if nd.get(key):
            entry["review_commit_sha"] = nd[key]
            break
    if nd.get("source_path"):
        entry["source_path"] = nd["source_path"]

    return review_id, entry


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_issues_from_github(reviews_repo: str, token: Optional[str]) -> List[Dict[str, Any]]:
    q = f'repo:{reviews_repo} is:issue "nd-review"'
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(q)}&per_page=100"
    data = _http_get_json(url, token=token)
    return list(data.get("items") or [])


def load_issues_from_fixture(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "items" in data:
        return list(data["items"])
    if isinstance(data, list):
        return data
    raise ValueError("Fixture must be a list of issues or a search response with 'items'.")


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------

def build_registry(issues: List[Dict[str, Any]], reviews_repo: str) -> Dict[str, Any]:
    entries: Dict[str, Any] = {}

    for issue in issues:
        review_id, entry = _issue_to_entry(issue)
        if not review_id:
            continue

        # Duplicate review_id: keep entry with higher-precedence state
        existing = entries.get(review_id)
        if existing:
            old_rank = STATE_PRECEDENCE.index(existing.get("state", "unreviewed"))
            new_rank = STATE_PRECEDENCE.index(entry.get("state", "unreviewed"))
            if new_rank < old_rank:
                entries[review_id] = entry
        else:
            entries[review_id] = entry

    return {
        "version": 2,
        "generated_at": _utc_now_iso(),
        "source": {
            "type": "github-issues",
            "repo": reviews_repo,
        },
        "reviews": entries,
    }


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------

def _git_latest_sha(repo_dir: Path, filepath: str) -> Optional[str]:
    """Return the SHA of the latest commit that touched `filepath`."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H", "-1", "--", filepath],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        sha = result.stdout.strip()
        return sha if sha else None
    except Exception:
        return None


def apply_staleness(registry: Dict[str, Any], repo_dir: Path) -> int:
    """For every 'reviewed' entry with review_commit_sha + source_path,
    check if the file was modified after the recorded SHA.  If so, mark
    the entry as stale.  Returns the number of entries marked stale."""
    stale_count = 0
    for review_id, entry in registry.get("reviews", {}).items():
        if entry.get("state") != "reviewed":
            continue
        recorded_sha = entry.get("review_commit_sha")
        source_path = entry.get("source_path")
        if not recorded_sha or not source_path:
            continue
        # source_path is relative to books/; git log needs repo-root-relative path
        git_path = f"books/{source_path}"
        latest_sha = _git_latest_sha(repo_dir, git_path)
        if latest_sha and latest_sha != recorded_sha:
            entry["state"] = "stale"
            entry["stale_reason"] = (
                f"File modified after review (latest: {latest_sha[:12]}, "
                f"reviewed at: {recorded_sha[:12]})"
            )
            stale_count += 1
    return stale_count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate NeurodeskEDU reviews registry.")
    parser.add_argument("--reviews-repo",
                        default=os.environ.get("ND_REVIEWS_REPO", "neurodesk/neurodeskedu-reviews"))
    parser.add_argument("--out",
                        default=os.environ.get("ND_REVIEWS_OUT", "books/_static/reviews.json"))
    parser.add_argument("--fixture", default=None,
                        help="Load issues from this JSON file instead of the GitHub API.")
    parser.add_argument("--repo-dir", default=None,
                        help="Path to the neurodeskedu repo checkout (for staleness detection).")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    issues = (load_issues_from_fixture(args.fixture)
              if args.fixture
              else load_issues_from_github(args.reviews_repo, token))

    registry = build_registry(issues, reviews_repo=args.reviews_repo)

    # Staleness detection
    stale_count = 0
    repo_dir = args.repo_dir or os.environ.get("ND_REPO_DIR")
    if repo_dir:
        stale_count = apply_staleness(registry, Path(repo_dir))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=False)
        f.write("\n")

    msg = f"Wrote {args.out} — {len(registry['reviews'])} review(s)"
    if stale_count:
        msg += f", {stale_count} marked stale"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
