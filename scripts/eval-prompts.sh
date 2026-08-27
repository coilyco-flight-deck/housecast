#!/bin/sh
# Compose one bundle per role and write its delivery as <out>/<role>.md, which
# is what evalkit.task sends as the system prompt. Frontier is the only tier
# every role supports, and model tier does not change selected context.
set -e
out=${1:-.evalkit/prompts}
mkdir -p "$out"

work=$(mktemp -d)
cleanup() { rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

uv run python -m housecast roster --out "$work/roster" >/dev/null
roles=$(python3 -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))['role_order']))" \
  "$work/roster/person.json")

for role in $roles; do
  uv run python -m housecast compose --role "$role" --delivery compiled \
    --model-tier frontier --out "$work/bundles/$role" >/dev/null
  cp "$work/bundles/$role/delivery/compiled.md" "$out/$role.md"
  printf '%s\t%s words\n' "$role" "$(wc -w < "$out/$role.md" | tr -d ' ')"
done
