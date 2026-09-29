#!/usr/bin/env python3
"""Hold back review issues for notebooks that have not passed CI on main.

Used by detect-new-notebooks.yml, which gives every notebook without an
nd_review_id a review ID and a review issue. This script decides which of those
candidates may go ahead. A notebook goes ahead only if the newest
"Run Notebook (<path>)" job for it, in a completed main-push run of
run_and_publish_notebooks.yml, succeeded on exactly the content checked out now.
On main that job also succeeds when it promotes a cached copy instead of
executing, but the cache only holds notebooks that passed on a review branch
with identical source, so that still counts as a pass.

Anything else is held back: no issue, no nd_review_id, just a warning, a line in
the step summary and an entry in the workflow's rolling "review-held" notice
issue. A held notebook still lacks an nd_review_id, so a later run
picks it up again once CI passes on main: after its failed job is re-run, or after
a push that changes it. Dispatched CI runs do not count.

Notebooks that already have a review issue (issue_exists, set by the reconcile
step) always go ahead: only their ID injection is left, and that sends nothing
new to reviewers.

Env:
  CANDIDATES_JSON  list of {source_path, review_id[, issue_exists]}
  GH_TOKEN         token with actions: read
  TRIGGER_RUN_ID   the CI run that triggered this workflow (optional)
  GITHUB_REPOSITORY, GITHUB_API_URL, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY (set by Actions)

Writes to GITHUB_OUTPUT: gated=<JSON list of candidates that may go ahead>,
count=<n>, and held=<JSON list of {source_path, reason, url}> (url may be null).
"""

import json
import os
import re
import subprocess
import urllib.request

CI_WORKFLOW = 'run_and_publish_notebooks.yml'
LOOKBACK_RUNS = 30  # newest completed main-push CI runs searched for a notebook's result
JOB_NAME = re.compile(r'^Run Notebook \((.+)\)$')
SKIP_LIST = '.github/skip-notebooks.txt'


def get_json(path):
    api = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
    req = urllib.request.Request(f'{api}/{path}', headers={
        'Authorization': f'Bearer {os.environ["GH_TOKEN"]}',
        'Accept': 'application/vnd.github+json',
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def ci_runs(repo, trigger_run_id=None):
    """Completed main-push runs of the CI workflow, newest first."""
    runs = get_json(
        f'repos/{repo}/actions/workflows/{CI_WORKFLOW}/runs'
        f'?branch=main&event=push&status=completed&per_page={LOOKBACK_RUNS}'
    )['workflow_runs']
    # The run that triggered us should already be listed; add it if the list lags.
    if trigger_run_id and all(str(r['id']) != str(trigger_run_id) for r in runs):
        runs.append(get_json(f'repos/{repo}/actions/runs/{trigger_run_id}'))
    return sorted(runs, key=lambda r: r['created_at'], reverse=True)


def notebook_jobs(repo, run_id):
    """{notebook path: job} for the Run Notebook jobs of a run's latest attempt."""
    jobs, page = {}, 1
    while True:
        data = get_json(
            f'repos/{repo}/actions/runs/{run_id}/jobs?filter=latest&per_page=100&page={page}'
        )
        for job in data['jobs']:
            m = JOB_NAME.match(job['name'])
            if m:
                jobs[m.group(1)] = job
        if not data['jobs'] or page * 100 >= data['total_count']:
            return jobs
        page += 1


def blob(rev, path):
    """Git blob id of books/<path> at <rev>, or None if it is not there."""
    out = subprocess.run(
        ['git', 'rev-parse', '--verify', '--quiet', f'{rev}:books/{path}'],
        capture_output=True, text=True,
    )
    return out.stdout.strip() or None


def skip_listed():
    try:
        with open(SKIP_LIST, encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip() and not line.startswith('#')}
    except FileNotFoundError:
        return set()


CONCLUSIONS = {'failure': 'CI failed', 'timed_out': 'CI timed out', 'cancelled': 'CI cancelled'}


def evaluate(candidates, runs, jobs_of, blob_at, head='HEAD', skipped=frozenset()):
    """Split candidates into (gated, held); held items are {source_path, reason, url}."""
    need = {c['source_path'] for c in candidates if not c.get('issue_exists')}
    newest = {}  # path -> (run, job) of the newest CI job for that notebook
    for run in runs:
        if need <= newest.keys():
            break
        for path, job in jobs_of(run).items():
            if path in need and path not in newest:
                newest[path] = (run, job)

    gated, held = [], []
    hold = lambda path, reason, url=None: held.append(
        {'source_path': path, 'reason': reason, 'url': url})
    for c in candidates:
        path = c['source_path']
        if c.get('issue_exists'):
            gated.append(c)  # already has a review issue: only the ID injection is left
        elif path not in newest:
            if path in skipped:
                hold(path, 'skip-listed: in .github/skip-notebooks.txt, so CI never runs it')
            else:
                hold(path, f'no finished CI result in the last {len(runs)} main runs '
                           '(still running, or not run)')
        else:
            run, job = newest[path]
            if blob_at(run['head_sha'], path) != blob_at(head, path):
                hold(path, 'stale: changed since CI last ran it; waiting for CI on this version',
                     run['html_url'])
            elif job['conclusion'] != 'success':
                reason = CONCLUSIONS.get(job['conclusion']) or (
                    f'CI {job["conclusion"]}' if job['conclusion'] else 'CI still running')
                hold(path, reason, job['html_url'])
            else:
                gated.append(c)
    return gated, held


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    candidates = json.loads(os.environ['CANDIDATES_JSON'])
    trigger = os.environ.get('TRIGGER_RUN_ID') or None
    if trigger:
        print(f'Triggered by CI run {trigger}')

    runs = ci_runs(repo, trigger) if any(not c.get('issue_exists') for c in candidates) else []
    gated, held = evaluate(
        candidates, runs, lambda run: notebook_jobs(repo, run['id']), blob,
        skipped=skip_listed(),
    )

    for c in gated:
        why = 'review issue already exists' if c.get('issue_exists') else 'passed CI'
        print(f"Go ahead: {c['source_path']} ({why})")
    for h in held:
        print(f"::warning::Review issue held back for {h['source_path']}: {h['reason']}"
              + (f" ({h['url']})" if h['url'] else '') + '. See the run summary to unblock it.')

    if held:
        lines = [
            '### Review issues held back until CI passes',
            '',
            'No review issue or `nd_review_id` was created for these notebooks. They stay '
            'pending until their current version passes CI on main. To unblock one, re-run '
            'its failed or cancelled job on that main run (possible for 30 days) or push a '
            'fix to the notebook. This workflow runs again when that CI run finishes. A '
            'manually dispatched CI run does not count.',
            '',
            '| Notebook | Reason | CI |',
            '|---|---|---|',
        ]
        lines += [f"| `{h['source_path']}` | {h['reason']} | "
                  + (f"[link]({h['url']})" if h['url'] else '') + ' |' for h in held]
        with open(os.environ.get('GITHUB_STEP_SUMMARY', os.devnull), 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

    with open(os.environ.get('GITHUB_OUTPUT', os.devnull), 'a', encoding='utf-8') as f:
        f.write(f'gated={json.dumps(gated)}\n')
        f.write(f'count={len(gated)}\n')
        f.write(f'held={json.dumps(held)}\n')


if __name__ == '__main__':
    main()
