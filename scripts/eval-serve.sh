#!/bin/sh
# Grade a committed run in a browser. Projects the roster into entities and
# renders the profile first, the same two inputs eval-annotate.sh builds.
#
# Without them `grade serve` falls back to the built-in three-type profile,
# whose label sets differ from the rendered one, and the pin check then reports
# drift on every voice case against a board that has not moved. See
# docs/grading-surfaces.md.
set -e

if [ $# -eq 0 ]; then
  echo "usage: just grade-serve RUN_DIR [OPTIONS]" >&2
  exit 2
fi
run=$1
shift

if [ ! -d "$run" ]; then
  echo "no run directory at $run" >&2
  exit 2
fi

render_dir=$(mktemp -d)
cleanup() { rm -rf "$render_dir"; }
trap cleanup EXIT HUP INT TERM
uv run python -m housecast roster --out "$render_dir" >/dev/null
uv run --extra eval python -m evalkit.roster \
  --person "$render_dir/person.json" \
  --out "$render_dir/entities.json"
uv run --extra eval python -m evalkit.profile --out "$render_dir/profile.yaml"

uv run --extra eval housecast grade serve "$run" \
  --profile "$render_dir/profile.yaml" \
  --roster "$render_dir/entities.json" \
  "$@"
