# Per-repo task manifest. Run `just` (or `just --list`) to see every verb.
#
# One line of comment per recipe on purpose: just reads only the LAST comment
# line above a recipe, so a wrapped description silently truncates to its tail.
#
# `.ward/ward.yaml` survives carrying catalog metadata only, because the catalog
# hooks upstream in agentic-os pin that exact path.

set positional-arguments

# Default target: list every available recipe.
default:
    @just --list --unsorted

# Run the offline gates: lint, format check, types, tests.
check *ARGS:
    @sh scripts/check.sh "$@"

# Run the unit test suite.
test *ARGS:
    @uv run --all-extras pytest "$@"

# Format Python sources.
format *ARGS:
    @uv run --all-extras ruff format housecast evalkit "$@"

# Check Python formatting without rewriting.
format-check *ARGS:
    @uv run --all-extras ruff format --check housecast evalkit "$@"

# Run the Python linter.
lint *ARGS:
    @uv run --all-extras ruff check housecast evalkit "$@"

# Run the Python type checker.
typecheck *ARGS:
    @uv run --all-extras mypy "$@"

# Run the repository validation hooks over all files.
pre-commit *ARGS:
    @pre-commit run --all-files "$@"

# Install the pre-commit and pre-push hooks into a fresh clone.
pre-commit-install *ARGS:
    @pre-commit install --hook-type pre-commit --hook-type pre-push "$@"

# Compose one role bundle. `just compose --role tpm --out DIR`.
compose *ARGS:
    @uv run python -m housecast compose "$@"

# Project the roster as person.json, which evalkit reads.
roster *ARGS:
    @uv run python -m housecast roster "$@"

# Print the roster field reference, rendered from the dataclasses.
fields *ARGS:
    @uv run python -m housecast fields "$@"

# Re-vendor roster.yaml's bodies and acts. `just sync-roster ../agent-compose/seed/roster/data`.
sync-roster *ARGS:
    @uv run python scripts/sync-roster.py "$@"

# Re-vendor the coilyco kit's primitives into the grading page. `just sync-kit ../website`.
sync-kit *ARGS:
    @uv run python scripts/sync_kit.py "$@"

# Report grading-page palette drift from the kit. Skips with no website checkout.
sync-kit-check *ARGS:
    @uv run python scripts/sync_kit.py --check "$@"

# Sync the engine and eval dependencies.
sync *ARGS:
    @uv sync --all-extras "$@"

# Refuse a publish whose tag disagrees with the packaged version. `just release-check housecast-v0.3.0`.
release-check *ARGS:
    @uv run python scripts/release_tag.py "$@"

# Build the sdist and wheel into dist/.
build *ARGS:
    @uv build "$@"

# Upload dist/ to PyPI. Reads the token from UV_PUBLISH_TOKEN, never from argv.
publish *ARGS:
    @uv publish --trusted-publishing never --check-url https://pypi.org/simple/housecast/ "$@"

# Upload dist/ to TestPyPI, the throwaway index. Same token variable, different registry.
publish-test *ARGS:
    @uv publish --trusted-publishing never --publish-url https://test.pypi.org/legacy/ --check-url https://test.pypi.org/simple/housecast/ "$@"

# Print the case list the current roster implies.
evalkit-matrix *ARGS:
    @sh scripts/eval-matrix.sh "$@"

# Report cases the roster implies but nobody wrote, graded, or still derives.
evalkit-coverage *ARGS:
    @uv run --extra eval python -m evalkit.coverage "$@"

# Compose one compiled bundle per role as the eval system prompts.
evalkit-prompts *ARGS:
    @sh scripts/eval-prompts.sh "$@"

# One live request through Agent Proxy, before a full board run.
evalkit-smoke *ARGS:
    @sh scripts/eval-smoke.sh "$@"

# Run the board through Inspect against Agent Proxy.
evalkit-run *ARGS:
    @sh scripts/eval-run.sh "$@"

# Open the Inspect log viewer.
evalkit-view *ARGS:
    @uv run --extra eval inspect view --log-dir .evalkit/logs "$@"

# Project a committed run into a display payload, one way only.
evalkit-export *ARGS:
    @uv run --extra eval housecast grade export "$@"

# Read an Inspect eval log and build the dataset the annotator grades.
evalkit-filter *ARGS:
    @uv run --extra eval python -m evalkit.filter "$@"

# Cluster annotation critiques into a ranked failure taxonomy.
evalkit-taxonomy *ARGS:
    @uv run --extra eval housecast grade taxonomy "$@"

# Annotate the eval dataset by hand, one keystroke per challenge.
evalkit-annotate *ARGS:
    @sh scripts/eval-annotate.sh "$@"

# Emit this board's profile as YAML, for a grading surface that takes --profile.
evalkit-profile *ARGS:
    @uv run --extra eval python -m evalkit.profile "$@"

# Project the roster as entities.json, the --roster a grading surface takes.
evalkit-entities *ARGS:
    @sh scripts/eval-entities.sh "$@"

# Pin or check the five grade inputs. `just grade-pin --dataset D --roster R`.
grade-pin *ARGS:
    @uv run --extra eval housecast grade pin "$@"

# Grade one committed run in a browser. `just grade-serve evaluations/pilot/RUN`.
grade-serve *ARGS:
    @uv run --extra eval housecast grade serve "$@"

# How often two graders split a case. `just grade-disagreement --dataset D --annotations A --annotations B --tester a --tester b`.
grade-disagreement *ARGS:
    @uv run --extra eval housecast grade disagreement "$@"

# Build the room-facing deck. `just grade-deck ROUNDS --run RUN_DIR --out DECK`.
grade-deck *ARGS:
    @uv run --extra eval housecast grade deck "$@"

# Write a graded run into a self-contained copy of the page. `just grade-seal RUN --out B.html`.
grade-seal *ARGS:
    @uv run --extra eval housecast grade seal "$@"

# Serve a built deck to a room, with anonymous voting. `just grade-present DECK`.
grade-present *ARGS:
    @uv run --extra eval housecast grade present "$@"
