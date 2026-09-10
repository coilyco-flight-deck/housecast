#!/bin/sh
# Project the roster into entities.json, the --roster every grading surface takes.
# eval-annotate.sh renders this into a temp directory it deletes, so before this
# script the only way to obtain the file was to launch the interactive annotator.
set -e
out=${1:-.evalkit/entities.json}
mkdir -p "$(dirname "$out")"

render_dir=$(mktemp -d)
cleanup() { rm -rf "$render_dir"; }
trap cleanup EXIT HUP INT TERM

uv run python -m housecast roster --out "$render_dir" >/dev/null
uv run --extra eval python -m evalkit.roster \
  --person "$render_dir/person.json" \
  --out "$out"
echo "wrote $out"
