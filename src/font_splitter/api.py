from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any

import tinycss2
from fontTools.ttLib import TTFont
from tinycss2.serializer import serialize_string_value, serialize_url

from .planner import Plan, PlannedBucket, plan_buckets
from .ranges import compress_codepoints
from .sources import RangeSource
from .subsetter import FontInput, load_font, subset_font
from .unicode_blocks import UnicodeBlockSource


_DEFAULT_FALLBACK = object()


@dataclass(frozen=True)
class SplitStats:
    matched_source_count: int
    planned_bucket_count: int
    total_codepoint_count: int
    fallback_codepoint_count: int
    empty_bucket_count: int
    overlap_dropped: int
    max_bucket_codepoint_count: int
    estimated_files: list[str]


@dataclass(frozen=True)
class SplitPlan:
    buckets: list[PlannedBucket]
    stats: SplitStats


@dataclass(frozen=True)
class SplitResult:
    """Result returned by both output modes.

    `assets` is populated by `split_font_to_memory()`. `assets_written` is
    populated by `split_font()` so disk output can avoid retaining every subset
    byte string in memory.
    """

    assets: dict[str, bytes]
    buckets: list[PlannedBucket]
    stats: SplitStats
    warnings: list[str]
    assets_written: list[Path]


@dataclass(frozen=True)
class _PreparedSplit:
    raw_font: bytes
    plan: Plan
    stats: SplitStats
    output_family: str
    base: str
    local_names: list[str]


@dataclass(frozen=True)
class _GeneratedSubset:
    name: str
    data: bytes
    css: str
    warnings: list[str]


def split_font_to_memory(
    font: FontInput,
    *,
    sources: list[RangeSource] | None = None,
    fallback: RangeSource | None | object = _DEFAULT_FALLBACK,
    max_codepoints: int | None = 1024,
    flavor: str = "woff2",
    family: str | None = None,
    style: str = "normal",
    weight: str | int = 400,
    stretch: str | None = None,
    local_src: str | list[str] = "auto",
) -> SplitResult:
    """Generate subset font files and CSS in memory."""

    prepared = _prepare_split(
        font,
        sources=sources,
        fallback=fallback,
        max_codepoints=max_codepoints,
        flavor=flavor,
        family=family,
        local_src=local_src,
    )
    assets: dict[str, bytes] = {}
    css_parts: list[str] = []
    warnings: list[str] = []

    for subset_asset in _iter_subset_assets(
        prepared,
        flavor=flavor,
        style=style,
        weight=weight,
        stretch=stretch,
    ):
        assets[subset_asset.name] = subset_asset.data
        warnings.extend(subset_asset.warnings)
        css_parts.append(subset_asset.css)

    assets[f"{prepared.base}.css"] = "\n".join(css_parts).encode("utf-8")
    return SplitResult(
        assets=assets,
        buckets=prepared.plan.buckets,
        stats=prepared.stats,
        warnings=list(dict.fromkeys(warnings)),
        assets_written=[],
    )


def split_font(
    font: FontInput,
    *,
    output_dir: str | PathLike[str],
    sources: list[RangeSource] | None = None,
    fallback: RangeSource | None | object = _DEFAULT_FALLBACK,
    max_codepoints: int | None = 1024,
    flavor: str = "woff2",
    family: str | None = None,
    style: str = "normal",
    weight: str | int = 400,
    stretch: str | None = None,
    local_src: str | list[str] = "auto",
) -> SplitResult:
    """Write subset font files and CSS to `output_dir` without retaining assets."""

    prepared = _prepare_split(
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
    written: list[Path] = []
    css_parts: list[str] = []
    warnings: list[str] = []

    for subset_asset in _iter_subset_assets(
        prepared,
        flavor=flavor,
        style=style,
        weight=weight,
        stretch=stretch,
    ):
        path = output_path / subset_asset.name
        path.write_bytes(subset_asset.data)
        written.append(path)
        warnings.extend(subset_asset.warnings)
        css_parts.append(subset_asset.css)

    css_path = output_path / f"{prepared.base}.css"
    css_path.write_text("\n".join(css_parts), encoding="utf-8")
    written.append(css_path)

    return SplitResult(
        assets={},
        buckets=prepared.plan.buckets,
        stats=prepared.stats,
        warnings=list(dict.fromkeys(warnings)),
        assets_written=written,
    )


def plan_font(
    font: FontInput,
    *,
    sources: list[RangeSource] | None = None,
    fallback: RangeSource | None | object = _DEFAULT_FALLBACK,
    max_codepoints: int | None = 1024,
    flavor: str = "woff2",
    family: str | None = None,
    local_src: str | list[str] = "auto",
) -> SplitPlan:
    """Plan output buckets and file names without running FontTools subsetting."""

    prepared = _prepare_split(
        font,
        sources=sources,
        fallback=fallback,
        max_codepoints=max_codepoints,
        flavor=flavor,
        family=family,
        local_src=local_src,
    )
    return SplitPlan(buckets=prepared.plan.buckets, stats=prepared.stats)


def _prepare_split(
    font: FontInput,
    *,
    sources: list[RangeSource] | None,
    fallback: RangeSource | None | object,
    max_codepoints: int | None,
    flavor: str,
    family: str | None,
    local_src: str | list[str],
) -> _PreparedSplit:
    raw_font = _read_font_bytes(font)
    ttfont = load_font(raw_font)
    cmap = set(ttfont.getBestCmap())
    output_family = family or _font_family(ttfont) or "Font Splitter"
    base = _slug(output_family)
    fallback_source = UnicodeBlockSource() if fallback is _DEFAULT_FALLBACK else fallback
    plan = plan_buckets(
        cmap,
        sources or [],
        fallback=fallback_source,
        max_codepoints=max_codepoints,
    )
    stats = _split_stats(plan, base=base, flavor=flavor)
    return _PreparedSplit(
        raw_font=raw_font,
        plan=plan,
        stats=stats,
        output_family=output_family,
        base=base,
        local_names=_local_names(ttfont, local_src),
    )


def _read_font_bytes(font: FontInput) -> bytes:
    if isinstance(font, bytes):
        return font
    if hasattr(font, "read"):
        return font.read()
    return Path(font).read_bytes()


def _iter_subset_assets(
    prepared: _PreparedSplit,
    *,
    flavor: str,
    style: str,
    weight: str | int,
    stretch: str | None,
) -> Iterator[_GeneratedSubset]:
    for bucket in prepared.plan.buckets:
        file_name = f"{prepared.base}.{bucket.id}.{flavor}"
        subset_result = subset_font(prepared.raw_font, bucket.codepoints, flavor=flavor)
        yield _GeneratedSubset(
            name=file_name,
            data=subset_result.data,
            warnings=subset_result.warnings,
            css=_font_face_css(
                family=prepared.output_family,
                file_name=file_name,
                flavor=flavor,
                codepoints=bucket.codepoints,
                style=style,
                weight=weight,
                stretch=stretch,
                local_names=prepared.local_names,
            ),
        )


def _font_family(font: TTFont) -> str | None:
    names = font["name"]
    return names.getDebugName(1)


def _font_full_name(font: TTFont) -> str | None:
    names = font["name"]
    return names.getDebugName(4)


def _font_style(font: TTFont) -> str | None:
    names = font["name"]
    return names.getDebugName(2)


def _local_names(font: TTFont, local_src: str | list[str]) -> list[str]:
    if not isinstance(local_src, str):
        return local_src
    if local_src == "none":
        return []
    if local_src != "auto":
        return [local_src]
    family = _font_family(font)
    style = _font_style(font)
    synthesized_full_name = f"{family} {style}" if family and style else None
    names = [_font_full_name(font), synthesized_full_name, font["name"].getDebugName(6)]
    return list(dict.fromkeys(name for name in names if name))


def _font_face_css(
    *,
    family: str,
    file_name: str,
    flavor: str,
    codepoints: set[int],
    style: str,
    weight: str | int,
    stretch: str | None,
    local_names: list[str],
) -> str:
    sources = [
        *(f"local({_css_quoted_string(name)})" for name in local_names),
        f"url({_css_url(file_name)}) format({_css_quoted_string(flavor)})",
    ]
    lines = [
        "@font-face {",
        f"  font-family: {_css_quoted_string(family)};",
        f"  font-style: {_css_component_value(style, property_name='font-style')};",
        f"  font-weight: {_css_component_value(weight, property_name='font-weight')};",
    ]
    if stretch:
        lines.append(
            f"  font-stretch: {_css_component_value(stretch, property_name='font-stretch')};"
        )
    lines.extend(
        [
            "  font-display: swap;",
            f"  src: {', '.join(sources)};",
            f"  unicode-range: {', '.join(compress_codepoints(codepoints))};",
            "}",
        ]
    )
    return "\n".join(lines)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return slug or "font"


def _split_stats(plan: Plan, *, base: str, flavor: str) -> SplitStats:
    estimated_font_files = [
        f"{base}.{bucket.id}.{flavor}"
        for bucket in plan.buckets
    ]
    return SplitStats(
        matched_source_count=plan.matched_source_count,
        planned_bucket_count=len(plan.buckets),
        total_codepoint_count=plan.total_codepoint_count,
        fallback_codepoint_count=plan.fallback_codepoint_count,
        empty_bucket_count=plan.empty_dropped,
        overlap_dropped=plan.overlap_dropped,
        max_bucket_codepoint_count=plan.max_bucket_codepoint_count,
        estimated_files=[*estimated_font_files, f"{base}.css"],
    )


def _css_quoted_string(value: Any) -> str:
    return f'"{serialize_string_value(_css_string_value(value))}"'


def _css_url(value: Any) -> str:
    return serialize_url(_css_string_value(value))


def _css_string_value(value: Any) -> str:
    return str(value).replace("\x00", "\uFFFD")


def _css_component_value(value: Any, *, property_name: str) -> str:
    raw_value = _css_string_value(value)
    normalized = raw_value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    if not normalized.strip():
        raise ValueError(f"Invalid CSS value for {property_name}: {raw_value!r}")
    tokens = tinycss2.parse_component_value_list(
        normalized,
        skip_comments=True,
    )
    serialized = tinycss2.serialize(tokens).strip()
    if not serialized or _contains_unsafe_css_component(tokens):
        raise ValueError(f"Invalid CSS value for {property_name}: {raw_value!r}")
    return serialized


def _contains_unsafe_css_component(tokens: list[Any]) -> bool:
    for token in tokens:
        if token.type == "error":
            return True
        if token.type == "literal" and token.value in {";", "{", "}"}:
            return True
    return False
