# Python Font Splitter v2 Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Node.js implementation with a Python-only FontTools package that keeps the useful v1 CLI behavior and adds the v2 source-planning API.

**Architecture:** Promote the validated POC into a root `src/font_splitter` package. The CLI and Python API share the same planning, subsetting, and CSS generation code. Docker installs the Python package and runs the `font-splitter` console script.

**Tech Stack:** Python 3.11+, FontTools with WOFF support, tinycss2, pytest, Docker Python slim image.

---

## Scope And Constraints

- Keep commits out of scope unless the user explicitly asks for one.
- Keep the POC directory as evidence until the production package passes local and Docker checks.
- Remove Node.js runtime/tooling only after Python tests pass.
- Use FontTools' bundled Unicode Blocks data instead of the old unversioned `src/unicodeBlocks` file.
- Preserve v1-compatible CLI options where practical: `--chunk`, `--flavor`, `--family`, `--italic`, `--weight`, `--dry`, `--output`, and deprecated `--quite`.
- Add v2 CLI options: `--source`, `--font-css-family`, `--font-css-weight`, `--font-css-style`, `--font-css-stretch`, `--no-fallback`, `--max-codepoints`, `--local-src`, and correctly spelled `--quiet`.

## File Structure

- Create `pyproject.toml`: Python package metadata, dependencies, CLI entrypoint, pytest config.
- Create `.gitignore`: local Python, Docker smoke, and OS-generated ignores.
- Create `src/font_splitter/`: production Python package.
- Create `tests/`: production pytest suite copied and adapted from the POC.
- Modify `Dockerfile`: Python-only build and entrypoint.
- Modify `README.md`: Python installation, API usage, CLI usage, Docker usage, and migration note.
- Delete `package.json`, `yarn.lock`, `tsconfig.json`, `commitlint.config.js`, `bin/font-splitter`, `src/app.js`, `src/resolve.js`, `src/font.css`, `src/banner.css`, and `src/unicodeBlocks` after Python verification.

### Task 1: Promote POC Package

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/font_splitter/*`
- Create: `tests/*`

- [ ] **Step 1: Copy POC package into production package**

Run:

```bash
mkdir -p src/font_splitter tests
cp poc/python-font-splitter-v2/src/font_splitter_poc/*.py src/font_splitter/
cp poc/python-font-splitter-v2/tests/*.py tests/
```

Expected: production package and tests exist, still importing `font_splitter_poc`.

- [ ] **Step 2: Rename test imports**

Run:

```bash
perl -pi -e 's/font_splitter_poc/font_splitter/g' tests/*.py
```

Expected: tests import `font_splitter`.

- [ ] **Step 3: Add root package metadata**

Create `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "font-splitter"
version = "0.2.0"
description = "Split large fonts into unicode-range webfont subsets"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [
  { name = "ViPro", email = "VdustR@gmail.com" },
]
dependencies = [
  "Brotli>=1.1.0",
  "fonttools[woff]>=4.63.0",
  "tinycss2>=1.4.0",
]

[project.scripts]
font-splitter = "font_splitter.cli:main"

[project.optional-dependencies]
test = [
  "pytest>=8.2.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/font_splitter"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 4: Add root ignore rules**

Create `.gitignore` with:

```gitignore
.DS_Store
.venv/
.pytest_cache/
__pycache__/
*.egg-info/
docker-input.ttf
docker-output/
output/
```

- [ ] **Step 5: Verify copied tests fail only because package behavior is still POC-level**

Run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -v
```

Expected: tests pass initially if copy is clean; follow-up tasks add production coverage.

### Task 2: Production Unicode Blocks Source

**Files:**
- Modify: `src/font_splitter/unicode_blocks.py`
- Modify: `tests/test_planner.py`

- [ ] **Step 1: Add tests for FontTools block data**

Add tests that assert fallback includes real Unicode blocks beyond the POC list, including `Latin Extended-A`, and that block IDs are slug-safe.

- [ ] **Step 2: Implement `UnicodeBlockSource` from `fontTools.unicodedata.Blocks`**

Build blocks from `Blocks.RANGES` and `Blocks.VALUES`, deriving inclusive end values from the next range start minus one, with the final range ending at `0x10FFFF`.

- [ ] **Step 3: Verify planner tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_planner.py -v
```

Expected: planner tests pass.

### Task 3: Production API And CSS Output

**Files:**
- Modify: `src/font_splitter/api.py`
- Modify: `src/font_splitter/css_source.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_css_source.py`

- [ ] **Step 1: Add API tests for defaults**

Add tests for default Unicode-block fallback, `bytes` input, file-like input, `local_src="auto"`, `local_src="none"`, and explicit local names.

- [ ] **Step 2: Implement defaults**

Make `split_font_to_memory()` default to `sources=None`, `fallback=UnicodeBlockSource()`, `max_codepoints=1024`, `flavor="woff2"`, `weight=400`, `style="normal"`, and `local_src="auto"`.

- [ ] **Step 3: Add CSS escaping and output metadata**

Escape CSS strings for single quotes and backslashes. Generate `font-style`, `font-weight`, and optional `font-stretch` from API/CLI values.

- [ ] **Step 4: Verify API tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_api.py tests/test_css_source.py -v
```

Expected: API and CSS source tests pass.

### Task 4: Production CLI

**Files:**
- Modify: `src/font_splitter/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add CLI tests**

Add tests for v1-compatible flags, `--chunk -`, `--quiet`, deprecated `--quite`, `--dry`, `--source font-css:<path>`, and `--no-fallback`.

- [ ] **Step 2: Implement argparse CLI**

Parse source flags in order. `font-css:<path>` creates a `FontCssSource.from_file(...)`; `unicode-blocks` creates a `UnicodeBlockSource`. If no source is provided and fallback is enabled, use Unicode blocks. If `--no-fallback` is set, do not append fallback. If `--dry` is set, print the plan but do not write assets.

- [ ] **Step 3: Verify CLI tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: CLI tests pass.

### Task 5: Docker And Documentation

**Files:**
- Modify: `Dockerfile`
- Modify: `README.md`

- [ ] **Step 1: Replace Dockerfile**

Use `python:3.12-slim`, install the package, set `WORKDIR /fonts`, and set `ENTRYPOINT ["font-splitter"]`.

- [ ] **Step 2: Rewrite README**

Document Python installation, CLI options, source ordering, Python API, Docker usage, and the v1 Node-to-Python migration note.

- [ ] **Step 3: Run Docker smoke**

Generate a tiny test font and run:

```bash
docker build -t font-splitter-python-v2 .
docker run --rm -v "$PWD:/fonts" font-splitter-python-v2 docker-input.ttf --output docker-output --flavor woff2 --quiet
```

Expected: CSS and WOFF2 files exist in `docker-output/`.

### Task 6: Remove Node.js Surface

**Files:**
- Delete: `package.json`
- Delete: `yarn.lock`
- Delete: `tsconfig.json`
- Delete: `commitlint.config.js`
- Delete: `bin/font-splitter`
- Delete: `src/app.js`
- Delete: `src/resolve.js`
- Delete: `src/font.css`
- Delete: `src/banner.css`
- Delete: `src/unicodeBlocks`

- [ ] **Step 1: Delete old files after Python checks pass**

Use structured file deletion, not shell `rm`.

- [ ] **Step 2: Verify no Node references remain**

Run:

```bash
rg -n "node|npm|yarn|typescript|commander|pyftsubset|package.json|bin/font-splitter" README.md Dockerfile pyproject.toml src tests
```

Expected: no stale Node runtime references. Mentions in migration notes are acceptable only when they explicitly describe v1.

### Task 7: Final Verification

**Files:**
- All changed files.

- [ ] **Step 1: Run full tests**

Run:

```bash
.venv/bin/python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Verify package CLI**

Run:

```bash
.venv/bin/font-splitter --help
```

Expected: help output includes v1-compatible and v2 source options.

- [ ] **Step 3: Inspect status**

Run:

```bash
git status --short
```

Expected: changes are scoped to docs, Python package, tests, Docker, README, and removal of Node files.

## Self-Review Notes

- This plan intentionally keeps the POC directory until the production package passes because it is useful evidence and a rollback reference.
- The plan avoids a custom VFS protocol. VFS-like integration remains `split_font_to_memory()` plus caller-managed writes.
- The plan does not claim full release readiness. Remaining release tasks include fixture policy finalization, real large-font integration fixtures, and warning capture hardening.
