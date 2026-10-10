"""Serve the static dashboard locally on port 5500."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "frontend"


def main() -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 5500), handler)
    print("Frontend running at http://127.0.0.1:5500")
    server.serve_forever()


if __name__ == "__main__":
    main()
