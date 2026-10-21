#!/usr/bin/env python3
"""Serve a local book build without caching stale HTML or application assets."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        # A cached page can send a conditional request after a rebuild. Always
        # send the current local file instead of retaining an older response.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / "books/_build/html"
    index = root / "index.html"
    if not index.exists():
        parser.error("Build first: python .github/scripts/build_book.py --base-url ''")
    if 'href="/edu/build/' in index.read_text():
        parser.error("This build uses /edu. Rebuild locally with --base-url ''")
    handler = partial(PreviewHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Local preview: http://localhost:{args.port}/ (caching disabled)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
