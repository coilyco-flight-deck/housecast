# Publishing to PyPI

How a `housecast-v*` tag becomes a release.

## The train

`.forgejo/workflows/publish.yml` fires on a pushed `housecast-v*` tag. It checks
the tag against the packaged version, runs `just check`, builds, then uploads.
`workflow_dispatch` retries a failed run against an existing tag. Publishing is
irreversible: PyPI accepts a filename once and yanking hides rather than
deletes, so both gates run before the build.

## The tag guard

`scripts/release_tag.py` refuses a tag naming a version other than the one in
`housecast/__init__.py`. That failure already happened in its softer form:
`housecast-v0.1.3` reports 0.1.1, and nothing caught it because a git dependency
does not check its metadata. Tested in `housecast/tests/test_release_tag.py`.

## The token

Trusted publishing needs GitHub, GitLab, Google, or ActiveState as the identity
provider, and Forgejo is none of them, so the train uses an API token.
`PYPI_TOKEN` is a repository Actions secret written from SSM
`/coilysiren/pypi/token` by agentic-os `just sync-actions-secrets`. It reaches
uv through `UV_PUBLISH_TOKEN` rather than argv, so no process listing carries
it. `just publish` passes `--check-url`, so a rerun after a partial upload skips
the files already on PyPI instead of failing on them.

## What ships

The wheel carries 66 entries: both packages, `housecast/data/roster.yaml`, the
grading page's fonts and motif, three `py.typed` markers, and both licence
files. The sdist is the whole tag, 607 KB compressed, of which `evaluations/` is
1,031,413 of 2,152,187 uncompressed bytes. It stays whole because two tests read
files under `evaluations/`, so trimming the run evidence breaks pytest there.

## See also

* [`FEATURES.md`](FEATURES.md) - the inventory.
