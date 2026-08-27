#!/bin/sh
# Print the case list the current roster implies. housecast projects the
# roster, evalkit derives the board, so adding a boundary changes this output
# on its own.
set -e
render_dir=$(mktemp -d)
cleanup() { rm -rf "$render_dir"; }
trap cleanup EXIT HUP INT TERM
uv run python -m housecast roster --out "$render_dir" >/dev/null
uv run python -m evalkit.matrix --roster "$render_dir/person.json" "$@"
