"""Run the subject as an HTTP MCP service: `python -m housecast.mcpeval.subject`.

A service rather than an in-process object, because the subject the customer
runs is a service. Hosting it in-process would make the loop's language
independence untestable, which is most of what it claims.
"""

from __future__ import annotations

import argparse

import uvicorn

from housecast.mcpeval.subject.server import app


def main() -> None:
    parser = argparse.ArgumentParser(prog="housecast.mcpeval.subject")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8931)
    args = parser.parse_args()
    uvicorn.run(app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
