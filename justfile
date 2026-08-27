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

# Sync the engine and eval dependencies.
sync *ARGS:
    @uv sync --all-extras "$@"

# Print the case list the current roster implies.
evalkit-matrix *ARGS:
    @sh scripts/eval-matrix.sh "$@"

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
    @uv run --extra eval aos-eval export "$@"

# Read an Inspect eval log and build the dataset the annotator grades.
evalkit-filter *ARGS:
    @uv run --extra eval python -m evalkit.filter "$@"

# Cluster annotation critiques into a ranked failure taxonomy.
evalkit-taxonomy *ARGS:
    @uv run --extra eval aos-eval taxonomy "$@"

# Annotate the eval dataset by hand, one keystroke per challenge.
evalkit-annotate *ARGS:
    @sh scripts/eval-annotate.sh "$@"
