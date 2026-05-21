# Agent Notes

## Project Direction

- This repository is now a Python-only package. Do not reintroduce TypeScript, Node.js runtime code, npm metadata, or shell-outs to FontTools CLIs.
- The canonical implementation lives in `src/font_splitter/`.
- Use FontTools' Python API for font loading/subsetting and `tinycss2` for font CSS parsing.
- Public API exports are managed in `src/font_splitter/__init__.py`. Keep `split_font()`, `split_font_to_memory()`, `plan_font()`, `FontCssSource`, and `UnicodeBlockSource` stable unless the user explicitly approves an API break.

## Architecture Invariants

- `split_font()` writes generated files to disk and should not retain every generated asset byte string in memory.
- `split_font_to_memory()` returns generated assets as `dict[str, bytes]` for VFS-like callers, zip generation, object storage, web responses, and tests.
- `plan_font()` must not run FontTools subsetting or write files.
- Range sources are ordered. Earlier sources win overlaps, and later sources only receive target-font codepoints that remain unassigned.
- The default fallback is `UnicodeBlockSource()`. Explicit CLI `--source unicode-blocks` disables the implicit fallback to avoid duplicated planning.
- `max_codepoints` is a planning bound on input codepoints. It is not a byte-size, glyph-count, or final-file-size guarantee.
- `FontCssSource` parses local CSS content/files only. Do not add URL fetching, `@import` following, or `src:` font downloads without a separate design discussion.
- CSS `unicode-range` support must include comma lists, explicit ranges, single codepoints, and wildcard ranges such as `U+4??`.

## Code Style

- Keep user-facing docs, code comments, commit messages, branch names, PR titles, and release notes in American English.
- Keep implementation small and explicit. Prefer focused modules over broad utility layers.
- Add comments only when behavior is easy to misunderstand, such as FontTools logging capture, release bootstrap state, or memory-vs-disk output behavior.
- Use generated in-memory fonts for unit tests. Do not commit third-party font binaries unless source URL, license, checksum, and necessity are documented.

## Verification

Run the narrowest relevant check first, then a full check before claiming completion.

```sh
.venv/bin/python -m pytest -v
.venv/bin/python -m compileall -q src/font_splitter tests
.venv/bin/python -m build
docker build -t font-splitter .
docker run --rm font-splitter --version
```

Optional downloaded-font integration tests require both environment variables:

```sh
FONT_SPLITTER_FIXTURE_URL=https://example.com/font.ttf \
FONT_SPLITTER_FIXTURE_SHA256=<sha256> \
.venv/bin/python -m pytest tests/test_downloaded_fixture.py -v
```

## Versioning

- The package version source is `[project].version` in `pyproject.toml`.
- Current Python rewrite target version: `0.2.0`.
- Last legacy npm release tag: `v0.1.5`.
- `.release-please-manifest.json` intentionally starts at `0.1.5`; `.github/release-please-config.json` uses `bootstrap-sha` to ignore old dependency-only history before the Python rewrite.
- After the first Release Please generated `v0.2.0` release PR has been merged, Release Please owns future version and changelog updates. Only remove or change `bootstrap-sha` in a deliberate release-maintenance change.

## Release Flow

- Release branch target is `main`. Verify the remote default branch before pushing or opening PRs because this repository previously used `master`.
- Use Conventional Commit titles. `fix:` maps to patch, `feat:` maps to minor, and `!` or `BREAKING CHANGE:` marks a breaking change. While the package is pre-`1.0.0`, breaking changes bump the minor version.
- `.github/workflows/semantic-pr.yml` checks PR titles so squash-merge commits stay compatible with Release Please. A Conventional Commit title can still be non-releasable; use `feat:`, `fix:`, or a breaking-change marker when a release is intended.
- Tags should keep the plain `vX.Y.Z` format, matching README GitHub install URLs. Keep `include-component-in-tag` disabled unless the install path is intentionally changed.
- On push to `main`, `.github/workflows/release-please.yml` opens or updates a Release Please PR.
- The workflow uses `RELEASE_PLEASE_TOKEN` when configured and falls back to `GITHUB_TOKEN`. Use `RELEASE_PLEASE_TOKEN` if release PR checks must run automatically from bot-created PR events.
- The Release Please PR should update `CHANGELOG.md`, `pyproject.toml`, `.release-please-manifest.json`, and versioned README install examples.
- Merging the Release Please PR creates the GitHub Release tag. The same workflow builds wheel and sdist artifacts and uploads them to the GitHub Release.
- PyPI publishing is not configured yet. Keep the documented install path as a GitHub tag URL until PyPI Trusted Publishing is intentionally added.

## Git Safety

- Read-only git inspection is safe.
- Do not commit, push, tag, create GitHub releases, change the default branch, or delete `master` unless the user explicitly asks.
- Before PR or release work, inspect current status, diff, recent commit style, workflow state, and release-related files.
