# Per-repo task manifest. Run `just` (or `just --list`) to see every verb.
#
# Recipes take trailing arguments directly: `just test -k roster`.
#
# One line of comment per recipe on purpose: just reads only the LAST comment
# line above a recipe, so a wrapped description silently truncates to its tail.
#
# `ward exec` is retired. `.ward/ward.yaml` survives carrying catalog metadata
# only, because check_catalog_block pins that exact path upstream.

set positional-arguments

# Default target: list every available recipe.
default:
    @just --list --unsorted

# Run the unit test suite.
test *ARGS:
    @uv run pytest "$@"

# Format Python sources.
format *ARGS:
    @uv run ruff format . "$@"

# Check Python formatting without rewriting.
format-check *ARGS:
    @uv run ruff format --check . "$@"

# Run the Python linter.
lint *ARGS:
    @uv run ruff check . "$@"

# Run the Python type checker.
typecheck *ARGS:
    @uv run mypy "$@"

# Run the repository validation hooks over all files.
pre-commit *ARGS:
    @pre-commit run --all-files "$@"

# Install the pre-commit and pre-push hooks into a fresh clone.
pre-commit-install *ARGS:
    @pre-commit install --hook-type pre-commit --hook-type pre-push "$@"
