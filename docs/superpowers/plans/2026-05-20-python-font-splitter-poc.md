# Python Font Splitter POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated Python POC that proves Font Splitter v2 can parse generic font CSS, plan range buckets, subset fonts through FontTools, output WOFF/WOFF2 in memory and on disk, and run in Docker.

**Architecture:** Keep the POC under `poc/python-font-splitter-v2/` so the current JavaScript implementation is not disturbed. Implement a small Python package with focused modules for range parsing, CSS source parsing, planning, FontTools subsetting, and a minimal CLI. Tests validate the high-risk technical assumptions before any full rewrite begins.

**Tech Stack:** Python 3.11+, FontTools with WOFF support, Brotli support, tinycss2, pytest, Docker Python slim image.

---

## Scope And Constraints

- Do not remove or modify the existing JavaScript/TypeScript implementation during this POC.
- Do not commit changes unless the user explicitly asks for a commit.
- Keep all POC source under `poc/python-font-splitter-v2/`.
- Keep the POC CLI minimal. It only needs to validate the design, not replace the v1 CLI.
- Use only redistributable or generated test fonts. Do not depend on system fonts in tests.

## File Structure

- Create `poc/python-font-splitter-v2/pyproject.toml`: POC package metadata, dependencies, and pytest config.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/__init__.py`: export POC API functions.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/ranges.py`: CSS `unicode-range` parsing and codepoint compression.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/css_source.py`: parse `@font-face` rules with `tinycss2`.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/unicode_blocks.py`: small vendored block list for POC fallback.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/planner.py`: ordered source planning, overlap handling, fallback, max split, no-split mode.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/subsetter.py`: FontTools in-memory and disk subsetting.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/api.py`: `split_font_to_memory()` and `split_font()`.
- Create `poc/python-font-splitter-v2/src/font_splitter_poc/cli.py`: minimal CLI for Docker and manual smoke tests.
- Create `poc/python-font-splitter-v2/tests/`: focused pytest suite.
- Create `poc/python-font-splitter-v2/tests/__init__.py`: make shared test helpers importable.
- Create `poc/python-font-splitter-v2/tests/helpers.py`: generated test font helper shared by integration tests.
- Create `poc/python-font-splitter-v2/Dockerfile`: Python-only Docker smoke image.
- Create `poc/python-font-splitter-v2/README.md`: POC-only usage and known boundaries.

### Task 1: Create Isolated Python POC Project

**Files:**
- Create: `poc/python-font-splitter-v2/pyproject.toml`
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/__init__.py`
- Create: `poc/python-font-splitter-v2/tests/__init__.py`
- Create: `poc/python-font-splitter-v2/README.md`

- [ ] **Step 1: Create project directories**

Run:

```bash
mkdir -p poc/python-font-splitter-v2/src/font_splitter_poc poc/python-font-splitter-v2/tests
```

Expected: directories exist under `poc/python-font-splitter-v2/`.

- [ ] **Step 2: Add `pyproject.toml`**

Create `poc/python-font-splitter-v2/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "font-splitter-poc"
version = "0.0.0"
description = "Python POC for Font Splitter v2"
requires-python = ">=3.11"
dependencies = [
  "Brotli>=1.1.0",
  "fonttools[woff]>=4.63.0",
  "tinycss2>=1.4.0",
]

[project.optional-dependencies]
test = [
  "pytest>=8.2.0",
]

[project.scripts]
font-splitter-poc = "font_splitter_poc.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Add package export file**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/__init__.py`:

```python
from .api import split_font, split_font_to_memory

__all__ = ["split_font", "split_font_to_memory"]
```

- [ ] **Step 4: Add tests package marker and POC README**

Create `poc/python-font-splitter-v2/tests/__init__.py`:

```python
```

Create `poc/python-font-splitter-v2/README.md`:

```markdown
# Python Font Splitter v2 POC

This directory validates the Python-only v2 design without modifying the current JavaScript implementation.

Validated assumptions:

- FontTools can subset fonts through the Python API without shelling out.
- WOFF and WOFF2 can be written to memory and disk.
- Generic `@font-face unicode-range` CSS can drive the first planning source.
- Remaining codepoints can fall back to Unicode blocks.
- The POC CLI can run inside a Python-only Docker image.

This is not the final v2 package layout.
```

- [ ] **Step 5: Install POC dependencies in an isolated virtualenv**

Run:

```bash
cd poc/python-font-splitter-v2
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

Expected: install succeeds and does not modify files outside the POC directory except normal Python package caches.

### Task 2: Implement Unicode Range Parsing

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/ranges.py`
- Create: `poc/python-font-splitter-v2/tests/test_ranges.py`

- [ ] **Step 1: Write failing parser tests**

Create `poc/python-font-splitter-v2/tests/test_ranges.py`:

```python
import pytest

from font_splitter_poc.ranges import compress_codepoints, parse_unicode_range_list


def test_parse_single_codepoint():
    assert parse_unicode_range_list("U+41") == {0x41}


def test_parse_range():
    assert parse_unicode_range_list("U+0041-0043") == {0x41, 0x42, 0x43}


def test_parse_wildcard():
    assert parse_unicode_range_list("U+4??") == set(range(0x400, 0x500))


def test_parse_comma_list_case_insensitive():
    assert parse_unicode_range_list("u+41, U+43-44") == {0x41, 0x43, 0x44}


def test_reject_invalid_range():
    with pytest.raises(ValueError, match="Invalid unicode-range"):
        parse_unicode_range_list("not-a-range")


def test_compress_codepoints():
    assert compress_codepoints({0x41, 0x42, 0x44}) == ["U+41-42", "U+44"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_ranges.py -v
```

Expected: FAIL because `font_splitter_poc.ranges` does not exist.

- [ ] **Step 3: Implement range parsing**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/ranges.py`:

```python
from __future__ import annotations

import re
from collections.abc import Iterable

_PART_RE = re.compile(r"^U\\+([0-9A-F?]+)(?:-([0-9A-F]+))?$", re.IGNORECASE)


def parse_unicode_range_list(value: str) -> set[int]:
    codepoints: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        codepoints.update(_parse_unicode_range_part(part))
    return codepoints


def _parse_unicode_range_part(part: str) -> set[int]:
    match = _PART_RE.match(part)
    if not match:
        raise ValueError(f"Invalid unicode-range: {part}")

    start_raw, end_raw = match.groups()
    if "?" in start_raw:
        if end_raw is not None:
            raise ValueError(f"Invalid unicode-range wildcard with explicit end: {part}")
        start = int(start_raw.replace("?", "0"), 16)
        end = int(start_raw.replace("?", "F"), 16)
        return set(range(start, end + 1))

    start = int(start_raw, 16)
    end = int(end_raw, 16) if end_raw is not None else start
    if end < start:
        raise ValueError(f"Invalid unicode-range end before start: {part}")
    return set(range(start, end + 1))


def compress_codepoints(codepoints: Iterable[int]) -> list[str]:
    ordered = sorted(set(codepoints))
    if not ordered:
        return []

    ranges: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for codepoint in ordered[1:]:
        if codepoint == previous + 1:
            previous = codepoint
            continue
        ranges.append((start, previous))
        start = previous = codepoint
    ranges.append((start, previous))

    return [
        f"U+{start:X}" if start == end else f"U+{start:X}-{end:X}"
        for start, end in ranges
    ]
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_ranges.py -v
```

Expected: PASS.

### Task 3: Parse Generic Font CSS Sources

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/css_source.py`
- Create: `poc/python-font-splitter-v2/tests/test_css_source.py`

- [ ] **Step 1: Write failing CSS source tests**

Create `poc/python-font-splitter-v2/tests/test_css_source.py`:

```python
import pytest

from font_splitter_poc.css_source import CssAmbiguityError, FontCssSource


CSS = """
/* latin */
@font-face {
  font-family: 'Demo Sans';
  font-style: normal;
  font-weight: 400;
  src: url(demo-latin.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}

/* symbols */
@font-face {
  font-family: 'Demo Sans';
  font-style: normal;
  font-weight: 400;
  src: url(demo-symbols.woff2) format('woff2');
  unicode-range: U+2600-2602, U+4??;
}
"""


def test_parse_font_css_rules_in_order():
    source = FontCssSource.from_css(CSS, family="Demo Sans", weight="400")
    buckets = source.buckets()
    assert [bucket.id for bucket in buckets] == ["font-css-001", "font-css-002"]
    assert buckets[0].label == "latin"
    assert 0x41 in buckets[0].codepoints
    assert 0x2601 in buckets[1].codepoints
    assert 0x4FF in buckets[1].codepoints


def test_requires_filter_when_descriptor_groups_are_ambiguous():
    css = CSS + """
@font-face {
  font-family: 'Other Sans';
  font-style: normal;
  font-weight: 400;
  unicode-range: U+0100-017F;
}
"""
    with pytest.raises(CssAmbiguityError):
        FontCssSource.from_css(css)


def test_ignores_rules_without_unicode_range():
    css = """
@font-face {
  font-family: 'Demo Sans';
  font-weight: 400;
  src: url(all.woff2);
}
"""
    source = FontCssSource.from_css(css)
    assert source.buckets() == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_css_source.py -v
```

Expected: FAIL because `font_splitter_poc.css_source` does not exist.

- [ ] **Step 3: Implement CSS source parsing**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/css_source.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tinycss2

from .ranges import parse_unicode_range_list


class CssAmbiguityError(ValueError):
    pass


@dataclass(frozen=True)
class RangeBucket:
    id: str
    label: str | None
    codepoints: set[int]


@dataclass(frozen=True)
class _FontFaceRule:
    descriptors: dict[str, str]
    label: str | None
    codepoints: set[int]


class FontCssSource:
    def __init__(self, rules: list[_FontFaceRule]) -> None:
        self._rules = rules

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        family: str | None = None,
        weight: str | int | None = None,
        style: str | None = None,
        stretch: str | None = None,
    ) -> "FontCssSource":
        return cls.from_css(
            Path(path).read_text(encoding="utf-8"),
            family=family,
            weight=weight,
            style=style,
            stretch=stretch,
        )

    @classmethod
    def from_css(
        cls,
        css: str,
        *,
        family: str | None = None,
        weight: str | int | None = None,
        style: str | None = None,
        stretch: str | None = None,
    ) -> "FontCssSource":
        raw_rules = _parse_font_face_rules(css)
        filtered = _filter_rules(
            raw_rules,
            family=family,
            weight=str(weight) if weight is not None else None,
            style=style,
            stretch=stretch,
        )
        return cls(filtered)

    def buckets(self) -> list[RangeBucket]:
        return [
            RangeBucket(
                id=f"font-css-{index:03d}",
                label=rule.label,
                codepoints=set(rule.codepoints),
            )
            for index, rule in enumerate(self._rules, start=1)
        ]


def _parse_font_face_rules(css: str) -> list[_FontFaceRule]:
    parsed = tinycss2.parse_stylesheet(css, skip_comments=False, skip_whitespace=True)
    rules: list[_FontFaceRule] = []
    pending_label: str | None = None

    for node in parsed:
        if node.type == "comment":
            text = node.value.strip()
            pending_label = text or None
            continue
        if node.type != "at-rule" or node.lower_at_keyword != "font-face" or node.content is None:
            pending_label = None
            continue

        declarations = tinycss2.parse_declaration_list(
            node.content,
            skip_comments=True,
            skip_whitespace=True,
        )
        descriptors: dict[str, str] = {}
        for declaration in declarations:
            if declaration.type != "declaration":
                continue
            descriptors[declaration.lower_name] = tinycss2.serialize(declaration.value).strip().strip("'\\\"")

        unicode_range = descriptors.get("unicode-range")
        if unicode_range:
            rules.append(
                _FontFaceRule(
                    descriptors=descriptors,
                    label=pending_label,
                    codepoints=parse_unicode_range_list(unicode_range),
                )
            )
        pending_label = None

    return rules


def _filter_rules(
    rules: list[_FontFaceRule],
    *,
    family: str | None,
    weight: str | None,
    style: str | None,
    stretch: str | None,
) -> list[_FontFaceRule]:
    descriptor_groups = {
        (
            rule.descriptors.get("font-family"),
            rule.descriptors.get("font-weight"),
            rule.descriptors.get("font-style"),
            rule.descriptors.get("font-stretch"),
        )
        for rule in rules
    }

    has_filter = any(value is not None for value in [family, weight, style, stretch])
    if len(descriptor_groups) > 1 and not has_filter:
        raise CssAmbiguityError("CSS contains multiple font descriptor groups; provide filters")

    filtered = []
    for rule in rules:
        if family is not None and rule.descriptors.get("font-family") != family:
            continue
        if weight is not None and rule.descriptors.get("font-weight") != weight:
            continue
        if style is not None and rule.descriptors.get("font-style") != style:
            continue
        if stretch is not None and rule.descriptors.get("font-stretch") != stretch:
            continue
        filtered.append(rule)
    return filtered
```

- [ ] **Step 4: Run CSS source tests**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_css_source.py -v
```

Expected: PASS.

### Task 4: Implement Planner With Fallback And No-Split

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/unicode_blocks.py`
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/planner.py`
- Create: `poc/python-font-splitter-v2/tests/test_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create `poc/python-font-splitter-v2/tests/test_planner.py`:

```python
from font_splitter_poc.css_source import RangeBucket
from font_splitter_poc.planner import PlannedBucket, plan_buckets
from font_splitter_poc.unicode_blocks import UnicodeBlockSource


class StaticSource:
    def __init__(self, buckets):
        self._buckets = buckets

    def buckets(self):
        return self._buckets


def test_source_order_and_overlap_first_wins():
    cmap = {0x41, 0x42, 0x43, 0x44}
    first = StaticSource([RangeBucket("first", "first", {0x41, 0x42})])
    second = StaticSource([RangeBucket("second", "second", {0x42, 0x43})])
    plan = plan_buckets(cmap, [first, second], fallback=None, max_codepoints=10)
    assert [bucket.id for bucket in plan.buckets] == ["first", "second"]
    assert plan.buckets[0].codepoints == {0x41, 0x42}
    assert plan.buckets[1].codepoints == {0x43}
    assert plan.overlap_dropped == 1


def test_fallback_remaining_to_unicode_blocks():
    cmap = {0x41, 0x42, 0x2600}
    first = StaticSource([RangeBucket("latin", "latin", {0x41})])
    plan = plan_buckets(cmap, [first], fallback=UnicodeBlockSource(), max_codepoints=10)
    assert [(bucket.id, bucket.codepoints) for bucket in plan.buckets] == [
        ("latin", {0x41}),
        ("Basic-Latin", {0x42}),
        ("Miscellaneous-Symbols", {0x2600}),
    ]


def test_max_codepoints_splits_all_buckets():
    cmap = {0x41, 0x42, 0x43}
    source = StaticSource([RangeBucket("latin", "latin", {0x41, 0x42, 0x43})])
    plan = plan_buckets(cmap, [source], fallback=None, max_codepoints=2)
    assert plan.buckets == [
        PlannedBucket("latin-001", "latin", {0x41, 0x42}),
        PlannedBucket("latin-002", "latin", {0x43}),
    ]


def test_no_split_mode_keeps_bucket_together():
    cmap = {0x41, 0x42, 0x43}
    source = StaticSource([RangeBucket("latin", "latin", {0x41, 0x42, 0x43})])
    plan = plan_buckets(cmap, [source], fallback=None, max_codepoints=None)
    assert plan.buckets == [
        PlannedBucket("latin", "latin", {0x41, 0x42, 0x43}),
    ]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_planner.py -v
```

Expected: FAIL because planner modules do not exist.

- [ ] **Step 3: Add POC Unicode blocks**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/unicode_blocks.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from .css_source import RangeBucket


@dataclass(frozen=True)
class UnicodeBlock:
    id: str
    start: int
    end: int


POC_BLOCKS = [
    UnicodeBlock("Basic-Latin", 0x0000, 0x007F),
    UnicodeBlock("Latin-1-Supplement", 0x0080, 0x00FF),
    UnicodeBlock("Miscellaneous-Symbols", 0x2600, 0x26FF),
    UnicodeBlock("CJK-Unified-Ideographs", 0x4E00, 0x9FFF),
]


class UnicodeBlockSource:
    def __init__(self, blocks: list[UnicodeBlock] | None = None) -> None:
        self._blocks = blocks or POC_BLOCKS

    def buckets(self) -> list[RangeBucket]:
        return [
            RangeBucket(block.id, block.id, set(range(block.start, block.end + 1)))
            for block in self._blocks
        ]
```

- [ ] **Step 4: Implement planner**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/planner.py`:

```python
from __future__ import annotations

from collections.abc import Iterable, Protocol
from dataclasses import dataclass

from .css_source import RangeBucket


class RangeSource(Protocol):
    def buckets(self) -> list[RangeBucket]:
        pass


@dataclass(frozen=True)
class PlannedBucket:
    id: str
    label: str | None
    codepoints: set[int]


@dataclass(frozen=True)
class Plan:
    buckets: list[PlannedBucket]
    overlap_dropped: int
    empty_dropped: int


def plan_buckets(
    cmap_codepoints: Iterable[int],
    sources: list[RangeSource],
    *,
    fallback: RangeSource | None,
    max_codepoints: int | None,
) -> Plan:
    available = set(cmap_codepoints)
    assigned: set[int] = set()
    buckets: list[PlannedBucket] = []
    overlap_dropped = 0
    empty_dropped = 0

    for source in [*sources, *([fallback] if fallback is not None else [])]:
        for candidate in source.buckets():
            in_font = candidate.codepoints & available
            overlap = in_font & assigned
            current = in_font - assigned
            overlap_dropped += len(overlap)
            if not current:
                empty_dropped += 1
                continue
            assigned.update(current)
            buckets.extend(_split_bucket(candidate.id, candidate.label, current, max_codepoints))

    return Plan(buckets=buckets, overlap_dropped=overlap_dropped, empty_dropped=empty_dropped)


def _split_bucket(
    bucket_id: str,
    label: str | None,
    codepoints: set[int],
    max_codepoints: int | None,
) -> list[PlannedBucket]:
    ordered = sorted(codepoints)
    if max_codepoints is None or len(ordered) <= max_codepoints:
        return [PlannedBucket(bucket_id, label, set(ordered))]

    chunks = [
        ordered[index : index + max_codepoints]
        for index in range(0, len(ordered), max_codepoints)
    ]
    width = len(str(len(chunks)))
    return [
        PlannedBucket(f"{bucket_id}-{index:0{width}d}", label, set(chunk))
        for index, chunk in enumerate(chunks, start=1)
    ]
```

- [ ] **Step 5: Run planner tests**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_planner.py -v
```

Expected: PASS.

### Task 5: Implement FontTools Memory And Disk Subsetting

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/subsetter.py`
- Create: `poc/python-font-splitter-v2/tests/helpers.py`
- Create: `poc/python-font-splitter-v2/tests/test_subsetter.py`

- [ ] **Step 1: Write failing subsetter tests**

Create `poc/python-font-splitter-v2/tests/helpers.py`:

```python
from io import BytesIO

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def build_test_font() -> bytes:
    glyph_order = [".notdef", "space", "A", "B", "C"]
    cmap = {0x20: "space", 0x41: "A", 0x42: "B", 0x43: "C"}
    advance_widths = {glyph: (600, 0) for glyph in glyph_order}

    glyphs = {}
    for glyph_name in glyph_order:
        pen = TTGlyphPen(None)
        glyphs[glyph_name] = pen.glyph()

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(advance_widths)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupOS2()
    fb.setupNameTable({"familyName": "POC Test", "styleName": "Regular"})
    fb.setupPost()
    fb.setupMaxp()

    out = BytesIO()
    fb.save(out)
    return out.getvalue()
```

Create `poc/python-font-splitter-v2/tests/test_subsetter.py`:

```python
from io import BytesIO

from fontTools.ttLib import TTFont

from font_splitter_poc.subsetter import subset_font_to_bytes
from tests.helpers import build_test_font


def test_subset_to_woff2_bytes_roundtrips():
    raw = build_test_font()
    out = subset_font_to_bytes(raw, {0x41, 0x42}, flavor="woff2")
    assert out[:4] == b"wOF2"
    font = TTFont(BytesIO(out))
    assert set(font.getBestCmap()) == {0x41, 0x42}


def test_subset_to_woff_bytes_roundtrips():
    raw = build_test_font()
    out = subset_font_to_bytes(raw, {0x41}, flavor="woff")
    assert out[:4] == b"wOFF"
    font = TTFont(BytesIO(out))
    assert set(font.getBestCmap()) == {0x41}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_subsetter.py -v
```

Expected: FAIL because `font_splitter_poc.subsetter` does not exist.

- [ ] **Step 3: Implement FontTools subsetter**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/subsetter.py`:

```python
from __future__ import annotations

from io import BytesIO
from os import PathLike
from typing import BinaryIO

from fontTools import subset
from fontTools.ttLib import TTFont

FontInput = str | PathLike[str] | bytes | BinaryIO


def load_font(font: FontInput) -> TTFont:
    if isinstance(font, bytes):
        return TTFont(BytesIO(font))
    return TTFont(font)


def subset_font_to_bytes(font: FontInput, codepoints: set[int], *, flavor: str) -> bytes:
    ttfont = load_font(font)
    options = subset.Options()
    options.flavor = flavor
    options.set(layout_features="*")
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(codepoints))
    subsetter.subset(ttfont)
    ttfont.flavor = flavor
    out = BytesIO()
    ttfont.save(out)
    return out.getvalue()
```

- [ ] **Step 4: Run subsetter tests**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_subsetter.py -v
```

Expected: PASS for both WOFF and WOFF2. If WOFF2 fails because Brotli support is unavailable, stop and fix package dependencies before continuing.

### Task 6: Implement High-Level Memory And Disk API

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/api.py`
- Create: `poc/python-font-splitter-v2/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `poc/python-font-splitter-v2/tests/test_api.py`:

```python
from pathlib import Path

from fontTools.ttLib import TTFont

from font_splitter_poc.api import split_font, split_font_to_memory
from font_splitter_poc.css_source import FontCssSource
from font_splitter_poc.unicode_blocks import UnicodeBlockSource
from tests.helpers import build_test_font


def test_split_font_to_memory_generates_css_and_woff2_assets():
    font = build_test_font()
    css = """
@font-face {
  font-family: 'POC Test';
  font-weight: 400;
  unicode-range: U+0041;
}
"""
    result = split_font_to_memory(
        font,
        sources=[FontCssSource.from_css(css, family="POC Test", weight="400")],
        fallback=UnicodeBlockSource(),
        max_codepoints=10,
        flavor="woff2",
        family="POC Test",
        local_src="none",
    )
    assert "POC-Test.font-css-001.woff2" in result.assets
    assert "POC-Test.Basic-Latin.woff2" in result.assets
    css_asset = result.assets["POC-Test.css"].decode("utf-8")
    assert "unicode-range: U+41;" in css_asset
    assert "local(" not in css_asset


def test_split_font_writes_assets_to_disk(tmp_path: Path):
    font = build_test_font()
    result = split_font(
        font,
        output_dir=tmp_path,
        sources=[],
        fallback=UnicodeBlockSource(),
        max_codepoints=None,
        flavor="woff",
        family="POC Test",
        local_src="auto",
    )
    assert (tmp_path / "POC-Test.Basic-Latin.woff").exists()
    assert (tmp_path / "POC-Test.css").exists()
    TTFont(tmp_path / "POC-Test.Basic-Latin.woff")
    css = (tmp_path / "POC-Test.css").read_text(encoding="utf-8")
    assert "local('POC Test Regular')" in css
    assert result.assets_written
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_api.py -v
```

Expected: FAIL because `font_splitter_poc.api` does not exist.

- [ ] **Step 3: Implement API**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/api.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import BinaryIO

from fontTools.ttLib import TTFont

from .planner import PlannedBucket, RangeSource, plan_buckets
from .ranges import compress_codepoints
from .subsetter import FontInput, load_font, subset_font_to_bytes


@dataclass(frozen=True)
class SplitResult:
    assets: dict[str, bytes]
    buckets: list[PlannedBucket]
    warnings: list[str]
    assets_written: list[Path]


def split_font_to_memory(
    font: FontInput,
    *,
    sources: list[RangeSource],
    fallback: RangeSource | None,
    max_codepoints: int | None,
    flavor: str,
    family: str | None,
    local_src: str | list[str],
) -> SplitResult:
    raw_font = _read_font_bytes(font)
    ttfont = load_font(raw_font)
    cmap = set(ttfont.getBestCmap())
    output_family = family or _font_family(ttfont) or "Font Splitter"
    base = _slug(output_family)

    plan = plan_buckets(cmap, sources, fallback=fallback, max_codepoints=max_codepoints)
    assets: dict[str, bytes] = {}
    css_parts: list[str] = []
    locals_for_css = _local_names(ttfont, local_src)

    for bucket in plan.buckets:
        file_name = f"{base}.{bucket.id}.{flavor}"
        font_bytes = subset_font_to_bytes(raw_font, bucket.codepoints, flavor=flavor)
        assets[file_name] = font_bytes
        css_parts.append(
            _font_face_css(
                family=output_family,
                file_name=file_name,
                flavor=flavor,
                codepoints=bucket.codepoints,
                local_names=locals_for_css,
            )
        )

    assets[f"{base}.css"] = "\\n".join(css_parts).encode("utf-8")
    return SplitResult(assets=assets, buckets=plan.buckets, warnings=[], assets_written=[])


def split_font(
    font: FontInput,
    *,
    output_dir: str | PathLike[str],
    sources: list[RangeSource],
    fallback: RangeSource | None,
    max_codepoints: int | None,
    flavor: str,
    family: str | None,
    local_src: str | list[str],
) -> SplitResult:
    result = split_font_to_memory(
        font,
        sources=sources,
        fallback=fallback,
        max_codepoints=max_codepoints,
        flavor=flavor,
        family=family,
        local_src=local_src,
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    written = []
    for name, data in result.assets.items():
        path = output_path / name
        path.write_bytes(data)
        written.append(path)
    return SplitResult(
        assets=result.assets,
        buckets=result.buckets,
        warnings=result.warnings,
        assets_written=written,
    )


def _read_font_bytes(font: FontInput) -> bytes:
    if isinstance(font, bytes):
        return font
    if hasattr(font, "read"):
        return font.read()
    return Path(font).read_bytes()


def _font_family(font: TTFont) -> str | None:
    names = font["name"]
    return names.getDebugName(1)


def _font_full_name(font: TTFont) -> str | None:
    names = font["name"]
    return names.getDebugName(4)


def _local_names(font: TTFont, local_src: str | list[str]) -> list[str]:
    if isinstance(local_src, list):
        return local_src
    if local_src == "none":
        return []
    if local_src != "auto":
        return [local_src]
    names = [_font_full_name(font), font["name"].getDebugName(6)]
    return [name for name in names if name]


def _font_face_css(
    *,
    family: str,
    file_name: str,
    flavor: str,
    codepoints: set[int],
    local_names: list[str],
) -> str:
    sources = [*(f"local('{name}')" for name in local_names), f"url({file_name}) format('{flavor}')"]
    return "\\n".join(
        [
            "@font-face {",
            f"  font-family: '{family}';",
            "  font-style: normal;",
            "  font-weight: 400;",
            "  font-display: swap;",
            f"  src: {', '.join(sources)};",
            f"  unicode-range: {', '.join(compress_codepoints(codepoints))};",
            "}",
        ]
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return slug or "font"
```

- [ ] **Step 4: Run API tests**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_api.py -v
```

Expected: PASS.

### Task 7: Add Minimal CLI And Docker Smoke

**Files:**
- Create: `poc/python-font-splitter-v2/src/font_splitter_poc/cli.py`
- Create: `poc/python-font-splitter-v2/tests/test_cli.py`
- Create: `poc/python-font-splitter-v2/Dockerfile`
- Modify: `poc/python-font-splitter-v2/README.md`

- [ ] **Step 1: Write failing CLI smoke test**

Create `poc/python-font-splitter-v2/tests/test_cli.py`:

```python
import subprocess
import sys

from tests.helpers import build_test_font


def test_cli_generates_woff2_and_css(tmp_path):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "font_splitter_poc.cli",
            str(font_path),
            "--output",
            str(output_dir),
            "--flavor",
            "woff2",
            "--max-codepoints",
            "-",
            "--local-src",
            "none",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "planned_buckets=" in completed.stdout
    assert (output_dir / "POC-Test.Basic-Latin.woff2").exists()
    assert (output_dir / "POC-Test.css").exists()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: FAIL because `font_splitter_poc.cli` does not exist.

- [ ] **Step 3: Implement minimal CLI**

Create `poc/python-font-splitter-v2/src/font_splitter_poc/cli.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from .api import split_font
from .unicode_blocks import UnicodeBlockSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("font_path")
    parser.add_argument("--output", default="output")
    parser.add_argument("--flavor", choices=["woff", "woff2"], default="woff2")
    parser.add_argument("--max-codepoints", default="1024")
    parser.add_argument("--local-src", default="none")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--quite", action="store_true")
    args = parser.parse_args(argv)

    max_codepoints = None if args.max_codepoints == "-" else int(args.max_codepoints)
    result = split_font(
        Path(args.font_path),
        output_dir=args.output,
        sources=[],
        fallback=UnicodeBlockSource(),
        max_codepoints=max_codepoints,
        flavor=args.flavor,
        family=None,
        local_src=args.local_src,
    )
    if not (args.quiet or args.quite):
        print(f"planned_buckets={len(result.buckets)}")
        print(f"assets={len(result.assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 5: Add Dockerfile**

Create `poc/python-font-splitter-v2/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

WORKDIR /work
ENTRYPOINT ["font-splitter-poc"]
```

- [ ] **Step 6: Build Docker image**

Run:

```bash
cd poc/python-font-splitter-v2
docker build -t font-splitter-python-poc .
```

Expected: image builds successfully.

- [ ] **Step 7: Add Docker note to POC README**

Append to `poc/python-font-splitter-v2/README.md`:

~~~markdown
## Docker Smoke

Build:

```sh
docker build -t font-splitter-python-poc .
```

Run with a mounted working directory:

```sh
docker run --rm -v "$PWD:/work" font-splitter-python-poc input.ttf --output output --flavor woff2
```
~~~

### Task 8: Run POC Verification Matrix

**Files:**
- No new files.

- [ ] **Step 1: Run the full Python test suite**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run focused WOFF and WOFF2 checks**

Run:

```bash
cd poc/python-font-splitter-v2
.venv/bin/python -m pytest tests/test_subsetter.py tests/test_api.py -v
```

Expected: all WOFF and WOFF2 roundtrip tests pass.

- [ ] **Step 3: Build Docker image**

Run:

```bash
cd poc/python-font-splitter-v2
docker build -t font-splitter-python-poc .
```

Expected: Docker build succeeds.

- [ ] **Step 4: Record POC results in README**

Append a concise verification section to `poc/python-font-splitter-v2/README.md`:

```markdown
## Verification

- `pytest -v`: passes
- WOFF roundtrip: passes
- WOFF2 roundtrip: passes
- Docker build: passes

Known POC boundaries:

- The CLI only validates the default Unicode block fallback path.
- The POC Unicode block table is intentionally small.
- Full warning capture is represented in API shape but not complete.
```

If a command fails, record the failing command and error summary instead of claiming success.

### Task 9: Self-Review The POC Diff

**Files:**
- Inspect all files under `poc/python-font-splitter-v2/`.

- [ ] **Step 1: Check no v1 files were modified**

Run:

```bash
git status --short
```

Expected: new files under `poc/python-font-splitter-v2/` and docs only; no modifications to `src/app.js`, `bin/font-splitter`, `package.json`, or `yarn.lock`.

- [ ] **Step 2: Check for unfinished markers**

Run:

```bash
rg -n "TB""D|TO""DO|FIX""ME" poc/python-font-splitter-v2
```

Expected: no matches.

- [ ] **Step 3: Check POC coverage against the design risks**

Verify these are true from tests or command output:

```text
FontTools API: tested by tests/test_subsetter.py
Memory output: tested by tests/test_api.py
Disk output: tested by tests/test_api.py
WOFF: tested by tests/test_subsetter.py
WOFF2: tested by tests/test_subsetter.py
Generic font CSS: tested by tests/test_css_source.py
Wildcard unicode-range: tested by tests/test_ranges.py
Overlap first-wins: tested by tests/test_planner.py
Fallback Unicode blocks: tested by tests/test_planner.py
No-split mode: tested by tests/test_planner.py and tests/test_cli.py
Deprecated --quite alias: represented in CLI parser
Docker: tested by docker build
```

- [ ] **Step 4: Report POC outcome**

Report:

```text
POC status: pass/fail
Verified:
- FontTools API:
- WOFF:
- WOFF2:
- memory output:
- disk output:
- generic font CSS:
- fallback planner:
- Docker:

Risks still open:
- Full Unicode Blocks data source
- Full CLI matrix
- FontTools warning capture completeness
- Large CJK fixture strategy
```

Do not commit unless the user explicitly asks for a commit.
