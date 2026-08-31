# Publishing to PyPI

How a `housecast-v*` tag becomes a release.

## The train

`.forgejo/workflows/publish.yml` fires on a pushed `housecast-v*` tag. It checks
the tag against the packaged version, runs `just check`, builds, then uploads.
Publishing is irreversible: PyPI accepts a filename once and yanking hides
rather than deletes, so both gates run before the build.

## The rehearsal

`workflow_dispatch` takes an `index` input defaulting to `testpypi`, so a
hand-run is harmless and a real upload is deliberate. A `testpypi` run skips the
tag guard and builds whatever the ref holds, proving build, auth, and upload
from a branch without spending a version. `pypi` retries a release by tag.

## The tag guard

`scripts/release_tag.py` refuses a tag naming a version other than the one in
`housecast/__init__.py`. That failure already happened in its softer form here:
`housecast-v0.1.3` reports 0.1.1, and a git dependency does not check metadata.
Tested in `housecast/tests/test_release_tag.py`.

## The tokens

Trusted publishing needs GitHub, GitLab, Google, or ActiveState as the identity
provider, and Forgejo is none of them, so the train uses API tokens. `PYPI_TOKEN`
and `TEST_PYPI_TOKEN` are repository Actions secrets written from SSM by
agentic-os `just sync-actions-secrets`, each reaching uv through
`UV_PUBLISH_TOKEN` rather than argv. Both recipes pass `--check-url`, so a rerun
after a partial upload skips files already on that index.

## What ships

The wheel carries 66 entries: both packages, `housecast/data/roster.yaml`, the
grading page's assets, three `py.typed` markers, and both licence files. The
sdist is the whole tag at 607 KB, because two tests read files under
`evaluations/` and trimming the run evidence breaks pytest there.
