# Python Font Splitter v2 Design

## Overview

Font Splitter v2 is a Python-only rewrite. It removes the TypeScript and Node.js implementation and makes Python plus FontTools the canonical implementation path.

The product remains a command-line font splitting tool, but the core should also be usable as a Python library. The CLI, Docker image, tests, and programmatic API should all call the same core implementation.

This is a breaking rewrite. The npm package and Node.js toolchain from v1 are not part of the v2 architecture.

## Goals

- Implement the core splitter in Python using the FontTools Python API.
- Support multiple ordered range sources, including generic font CSS and Unicode blocks.
- Fill remaining font coverage by default so template sources do not silently drop glyph coverage.
- Support local filesystem output and in-memory output from the same planning and subsetting behavior.
- Preserve v1's core CLI capabilities where they do not conflict with the Python-only rewrite.
- Provide Docker usage equivalent to the current project, but with a Python-only image.
- Add focused tests for CSS parsing, planning, subsetting, CSS output, and Docker behavior.

## Non-Goals

- Do not preserve the TypeScript or Node.js code path.
- Do not keep an npm wrapper in v2.
- Do not hand-roll OpenType subsetting logic.
- Do not create a custom virtual filesystem protocol in the core package.
- Do not use the old JavaScript implementation as the correctness oracle.
- Do not preserve v1 bugs or misspellings as the documented primary interface.

## Architecture

The package should be split into focused modules:

- `font_splitter.api`: high-level `split_font()` and `split_font_to_memory()`.
- `font_splitter.fonts`: font metadata and cmap extraction through FontTools.
- `font_splitter.sources`: range sources such as `FontCssSource` and `UnicodeBlockSource`.
- `font_splitter.planner`: ordered source pipeline, overlap handling, fallback planning, and bucket splitting.
- `font_splitter.subsetter`: FontTools subset integration.
- `font_splitter.css`: generated `@font-face` CSS.
- `font_splitter.cli`: command-line argument parsing and reporting.
- `font_splitter.fsspec`: optional filesystem helper layer, only if fsspec support is added.

The core should expose a small stable API first. Lower-level classes can exist for tests and advanced use, but the first public contract should center on the two high-level API functions.

## Public API

`split_font()` writes output assets to a local directory:

```python
result = split_font(
    font="NotoSansTC.ttf",
    output_dir="dist",
    sources=[
        FontCssSource.from_file(
            "noto-sans-tc.css",
            family="Noto Sans TC",
            weight=400,
        ),
        UnicodeBlockSource(),
    ],
    max_codepoints=1024,
    flavor="woff2",
)
```

`split_font_to_memory()` performs the same planning and subsetting, but returns generated assets instead of writing to disk:

```python
result = split_font_to_memory(
    font=font_bytes,
    sources=[
        FontCssSource.from_css(css_text, family="Noto Sans TC", weight=400),
        UnicodeBlockSource(),
    ],
    max_codepoints=1024,
    flavor="woff2",
)
```

Both functions should produce the same plan, bucket IDs, file names, CSS content, warnings, and statistics. The only difference is the output destination.

The `font` input should support:

- `os.PathLike`
- `str` paths
- `bytes`
- binary file-like objects

This matches FontTools' native `TTFont` support for paths and binary streams.

## VFS And File-Like Support

Core support should stay close to Python native IO and FontTools:

- Accept path-like values, bytes, and binary file-like objects for font input.
- Write local files in `split_font()`.
- Return asset bytes/text in `split_font_to_memory()`.

VFS support should not be implemented through a custom output protocol in the core. The generic integration path is `split_font_to_memory()`: callers can write returned assets to S3, GCS, zip files, databases, web responses, or application-specific storage.

If direct VFS helpers are added, they should use an existing library such as fsspec as an optional integration:

- `font-splitter[fsspec]`
- helper functions that accept fsspec URLs or an existing fsspec filesystem
- no fsspec dependency in the base install

The core should not expose a `filesystem="fsspec"` mode switch.

## Range Sources

The planner uses an ordered source pipeline. Each source emits candidate buckets, and the planner assigns only codepoints that:

- exist in the target font cmap
- have not already been assigned by an earlier source

Earlier sources win overlaps. Later sources only receive remaining codepoints.

### FontCssSource

`FontCssSource` should parse generic standards-shaped font CSS, not just Google Fonts CSS.

Rules:

- Parse CSS using a real CSS parser such as `tinycss2`.
- Use only `@font-face` rules that contain `unicode-range`.
- Support normal `unicode-range` ranges such as `U+0000-00FF`.
- Support CSS wildcard syntax such as `U+4??`.
- Preserve matching `@font-face` rule order from the input CSS.
- If the CSS contains multiple family, weight, style, or stretch groups, require explicit filters.
- If the CSS contains exactly one strict descriptor group, it may be used automatically.
- Ignore `src` URLs for subsetting. CSS is a range template, not a source font.
- Use comments only as best-effort metadata, not as stable IDs.

Bucket IDs should be stable by order, such as `font-css-001`. A nearby comment can be retained as a label or note for reports.

### UnicodeBlockSource

`UnicodeBlockSource` should cover remaining codepoints by Unicode block.

Rules:

- Use a versioned Unicode Blocks data source.
- Do not silently inherit the current unversioned `src/unicodeBlocks` file.
- Intersect every block with remaining target font codepoints.
- Split oversized block buckets by `max_codepoints`.

The Unicode data source can be vendored with a documented Unicode version or generated by a documented update script.

## Planning Rules

The planner should:

- preserve source order
- preserve CSS rule order
- preserve chunk order within each bucket
- preserve Unicode block order for fallback
- apply overlap first-wins
- drop empty buckets after cmap intersection
- collect statistics for overlap drops and empty buckets
- fill remaining codepoints by default with `UnicodeBlockSource`
- support an explicit template-only mode, such as `--no-fallback`

`max_codepoints` applies to every bucket, including font CSS buckets and fallback buckets.

`max_codepoints` is a planning limit on input codepoints. It does not guarantee the final glyph count or file size because FontTools may keep additional glyphs through composite glyphs, layout closure, or other font-internal requirements.

The v1 `--chunk -` behavior should be preserved as an explicit no-split mode. The v2 CLI can expose this as `--max-codepoints -`, `--no-chunk`, or both. The behavior means a bucket is not split by size after source and cmap filtering.

## Subsetting

Subsetting should use the FontTools Python API directly, not shell out to `pyftsubset`.

For each planned bucket:

- load the source font through FontTools
- populate a FontTools subsetter with bucket Unicode codepoints
- run subset
- set output flavor such as `woff2`
- save to bytes or path depending on the caller
- reload the generated font during tests for structural validation

FontTools warnings should be captured and included in `SplitResult.warnings`. CLI output should show a concise warning summary. Warnings should not be silently swallowed.

## Output

Output file names should be stable:

```text
<base>.<bucket-id>.<flavor>
<base>.css
```

Examples:

```text
NotoSansTC.font-css-001.woff2
NotoSansTC.font-css-002.woff2
NotoSansTC.CJK-Unified-Ideographs-001.woff2
NotoSansTC.css
```

The generated CSS should:

- include one `@font-face` per subset font
- preserve planner order
- default `font-family` from the input font name
- allow family, style, weight, and stretch overrides from CLI/API
- use actual bucket codepoints for `unicode-range`
- point `src` URLs at generated local subset file names

Font CSS source descriptors are used for source filtering. They should not automatically override output metadata unless a later explicit `inherit-from-source` feature is designed.

The CSS writer should support optional `local(...)` entries before generated `url(...)` sources. This preserves v1's ability to emit local font fallbacks while making the behavior explicit.

Recommended policy:

- `local_src="auto"`: derive local names from the input font metadata, matching v1's intent.
- `local_src="none"`: omit all `local(...)` entries.
- `local_src=["Name A", "Name B"]`: use caller-provided local names.

The CLI should expose the same behavior through an option such as `--local-src auto|none|<name>`. The implementation plan should decide the default. If strict v1 output compatibility is prioritized, the default should be `auto`; if webfont determinism is prioritized, the default should be `none` with an explicit v1 compatibility mode.

The required output flavors for v2 are `woff2` and `woff`, matching v1. `ttf` and `otf` output are not part of the primary v2 webfont splitter path.

## Reporting

Dry run output should report:

- matched source count
- planned bucket count
- total covered codepoints
- fallback codepoint count
- empty buckets after cmap intersection
- codepoints dropped from later buckets because of overlap
- max bucket codepoint count
- estimated output file names

Normal run output should include a condensed version of the same summary. This is important for CJK fonts and other broad-coverage fonts that may generate many subsets.

## CLI

The CLI entrypoint should remain:

```bash
font-splitter [options] <font-path>
```

The initial CLI should use repeated source flags so source order is explicit:

```bash
font-splitter NotoSansTC.ttf \
  --source font-css:noto-sans-tc.css \
  --source unicode-blocks \
  --font-css-family "Noto Sans TC" \
  --font-css-weight 400 \
  --max-codepoints 1024 \
  --flavor woff2 \
  --output dist
```

The CLI should support:

- input font path
- output directory
- output flavor
- max codepoints per planned bucket
- no-split mode equivalent to v1 `--chunk -`
- font CSS source path and filters
- Unicode blocks fallback
- no-fallback/template-only mode
- family/style/weight/stretch output overrides
- optional `local(...)` CSS source behavior
- dry run
- quiet or verbose reporting

The documented quiet flag should be spelled `--quiet`. The v1 misspelling `--quite` can be accepted as a deprecated alias for migration compatibility, but it should not be the primary documented spelling.

## Packaging

Use `pyproject.toml` as the only package configuration.

Recommended baseline:

- Python `>=3.11`, unless older environment support becomes a concrete requirement
- FontTools as a runtime dependency
- WOFF and WOFF2 support installed and verified through the package or Docker dependency set, such as `fonttools[woff]` plus Brotli support where required
- no Node.js package files or TypeScript config

README should document:

- `uvx font-splitter ...`
- `pipx install font-splitter`
- Python API usage
- Docker usage
- migration note from v1 npm/Node implementation

The repository can continue using Conventional Commits as a convention, but Node-based commit tooling should not remain part of v2.

## Docker

The Docker image should be Python-only:

- Python slim base
- install the package and FontTools WOFF2 dependencies
- `ENTRYPOINT ["font-splitter"]`
- volume usage similar to the current Docker interface

Docker tests should verify:

- the CLI runs
- WOFF2 output is produced
- WOFF output is produced
- generated CSS references generated subset files
- generated WOFF2 files can be read by FontTools
- generated WOFF files can be read by FontTools

## Testing

Unit tests should cover:

- CSS parsing with `tinycss2`
- CSS `unicode-range` wildcard expansion
- ambiguous CSS descriptor filtering
- missing `unicode-range` rules
- source ordering
- overlap first-wins
- fallback remaining codepoints
- `max_codepoints` splitting
- Unicode range compression
- stable filename generation
- CSS output order
- `local(...)` CSS source modes
- no-split mode equivalent to v1 `--chunk -`
- deprecated `--quite` alias if migration compatibility is kept

Integration tests should cover:

- `split_font_to_memory()` with a small fixture font
- `split_font()` writing local files
- WOFF2 roundtrip through `TTFont(BytesIO(...))`
- WOFF roundtrip through `TTFont(BytesIO(...))`
- subset cmap equals planned codepoint intersection for supported codepoints
- warning capture from FontTools
- Docker smoke test

Golden tests should compare:

- plan JSON or structured plan output
- generated CSS snapshots
- output asset names

The old JavaScript implementation should not be used as the only oracle because it has known issues around CSS linefeeds and incomplete coverage.

## Fixture Policy

Test fixtures must avoid unclear font redistribution rights.

Rules:

- Commit only small, redistributable test fonts with documented licenses.
- Download large or CJK fixtures through a checksum-verified test helper.
- Record source URL, license, and checksum for downloaded fixtures.
- Do not depend on system fonts for CI.
- Do not commit fonts with unclear redistribution rights.

Generated minimal fonts can be used for planner-focused tests, but they should not fully replace real font integration tests.

## Risks And Guardrails

- CSS parsing must use a real parser; regex parsing is too fragile.
- CSS `unicode-range` wildcard syntax must be supported or explicitly rejected with a clear error. v2 should support it.
- Comment-derived labels are not stable enough for file names; source order should define stable IDs.
- Ambiguous font CSS must require explicit filters.
- Overlap and empty bucket statistics must be visible in dry-run reports.
- Unicode Blocks data must be versioned.
- The coverage model is Unicode cmap codepoints, not full text shaping.
- Variation selectors, PUA, and complex shaping should be documented as advanced font behavior governed by FontTools closure, not guaranteed by the planner.
- WOFF and WOFF2 support must be verified in both local tests and Docker.
- Large CJK fallback can generate many files; planning summaries should make that visible before users run full generation.
- `local(...)` defaults are a product choice: `auto` is closer to v1, while `none` is more deterministic for webfont delivery and testing.

## Success Criteria

- v2 has no TypeScript or Node.js runtime/tooling dependency.
- CLI can split a small fixture font to WOFF, WOFF2, and CSS.
- Python API can split a font entirely in memory.
- Generic font CSS can be used as the first range source.
- Remaining font coverage falls back to Unicode blocks by default.
- Generated WOFF and WOFF2 files can be reloaded by FontTools.
- Generated CSS references all generated subset files.
- Docker can run the Python CLI and generate WOFF and WOFF2 output.
