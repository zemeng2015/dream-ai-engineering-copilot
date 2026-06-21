# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer


class SpaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        self._fallback_to_index_when_needed()
        super().do_GET()

    def do_HEAD(self) -> None:
        self._fallback_to_index_when_needed()
        super().do_HEAD()

    def _fallback_to_index_when_needed(self) -> None:
        clean_path = self.path.split("?", 1)[0].split("#", 1)[0]
        requested_path = Path(self.translate_path(clean_path))
        if not requested_path.exists() and not clean_path.startswith("/api/"):
            self.path = "/index.html"


class ReusableTCPServer(TCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Angular build with SPA fallback.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument(
        "--directory",
        default="frontend/dist/frontend/browser",
        help="Directory containing index.html.",
    )
    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    handler = lambda *handler_args, **handler_kwargs: SpaRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(directory),
        **handler_kwargs,
    )
    with ReusableTCPServer((args.host, args.port), handler) as server:
        print(f"Serving {directory} at http://{args.host}:{args.port}/")
        server.serve_forever()


if __name__ == "__main__":
    main()
