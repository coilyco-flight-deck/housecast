#!/bin/sh
# Offline gates. The pre-commit suite is managed by agentic-os, so repo-local
# Python linting runs here instead of being hand-added to that file.
set -e
uv run ruff check housecast evalkit
uv run ruff format --check housecast evalkit
uv run mypy
uv run pytest -q
