#!/bin/sh
# Compose one bundle per role and write its delivery as <out>/<role>.md, which
# is what evalkit.task sends as the system prompt. Frontier is the only tier
# every role supports, and model tier does not change selected context.
#
# agent-compose composes, not housecast - housecast#8041. `catalog roles
# --json` names the live roles, `compose <request.kdl>` renders each one's
# harness-agnostic compiled charter.
set -e
out=${1:-.evalkit/prompts}
mkdir -p "$out"

work=$(mktemp -d)
cleanup() { rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

# An archived role stays in the catalog but compose refuses it, so filter here
# on the same predicate evalkit.matrix.active_roles uses.
roles=$(agent-compose catalog roles --json | python3 -c "
import json, sys
print(' '.join(r['slug'] for r in json.load(sys.stdin)['items'] if not r.get('archived')))
")

for role in $roles; do
  printf 'compose {\n    role "%s"\n    delivery "compiled"\n    model-tier "frontier"\n}\n' \
    "$role" > "$work/$role.kdl"
  agent-compose compose "$work/$role.kdl" --out "$work/bundles/$role" >/dev/null
  compiled=$(find "$work/bundles/$role" -path '*/delivery/compiled.md')
  cp "$compiled" "$out/$role.md"
  printf '%s\t%s words\n' "$role" "$(wc -w < "$out/$role.md" | tr -d ' ')"
done
