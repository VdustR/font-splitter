from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .api import SplitStats, plan_font, split_font
from .css_source import FontCssSource
from .unicode_blocks import UnicodeBlockSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="font-splitter")
    parser.add_argument("-v", "--version", action="version", version=_version_text())
    parser.add_argument("font_path")
    parser.add_argument("-o", "--output", default="output")
    parser.add_argument("-f", "--flavor", choices=["woff", "woff2"], default="woff2")
    parser.add_argument(
        "-c",
        "--chunk",
        help="v1-compatible alias for --max-codepoints; '-' disables splitting",
    )
    parser.add_argument("--max-codepoints", default="1024")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="ordered range source: font-css:<path> or unicode-blocks",
    )
    parser.add_argument("--font-css-family")
    parser.add_argument("--font-css-weight")
    parser.add_argument("--font-css-style")
    parser.add_argument("--font-css-stretch")
    parser.add_argument("--no-fallback", action="store_true")
    parser.add_argument("-n", "--family")
    parser.add_argument("--style", default="normal")
    parser.add_argument("-i", "--italic", action="store_true")
    parser.add_argument("-w", "--weight", default=400)
    parser.add_argument("--stretch")
    parser.add_argument("-d", "--dry", action="store_true")
    parser.add_argument("--local-src", default="auto")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--quite", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    max_codepoints = _parse_max_codepoints(args.max_codepoints, args.chunk)
    sources = _parse_sources(args)
    fallback = None if args.no_fallback or _has_explicit_unicode_blocks(args.source) else UnicodeBlockSource()
    style = "italic" if args.italic else args.style

    split_kwargs = dict(
        sources=sources,
        fallback=fallback,
        max_codepoints=max_codepoints,
        flavor=args.flavor,
        family=args.family,
        style=style,
        weight=args.weight,
        stretch=args.stretch,
        local_src=args.local_src,
    )
    if args.dry:
        plan_kwargs = dict(split_kwargs)
        plan_kwargs.pop("style")
        plan_kwargs.pop("weight")
        plan_kwargs.pop("stretch")
        result = plan_font(Path(args.font_path), **plan_kwargs)
        asset_count = len(result.stats.estimated_files)
        warnings = []
    else:
        result = split_font(Path(args.font_path), output_dir=args.output, **split_kwargs)
        asset_count = len(result.assets_written)
        warnings = result.warnings

    if not (args.quiet or args.quite):
        _print_summary(result.stats, asset_count=asset_count, warning_count=len(warnings))
    return 0


def _parse_max_codepoints(max_codepoints: str | None, chunk: str | None) -> int | None:
    value = chunk if chunk is not None else max_codepoints
    if value == "-":
        return None
    return int(value or "1024")


def _parse_sources(args: argparse.Namespace):
    sources = []
    for raw_source in args.source:
        kind, _, value = raw_source.partition(":")
        if kind == "font-css" and value:
            sources.append(
                FontCssSource.from_file(
                    value,
                    family=args.font_css_family,
                    weight=args.font_css_weight,
                    style=args.font_css_style,
                    stretch=args.font_css_stretch,
                )
            )
        elif raw_source == "unicode-blocks":
            sources.append(UnicodeBlockSource())
        else:
            raise SystemExit(f"Unsupported source: {raw_source}")
    return sources


def _has_explicit_unicode_blocks(raw_sources: list[str]) -> bool:
    return "unicode-blocks" in raw_sources


def _print_summary(stats: SplitStats, *, asset_count: int, warning_count: int) -> None:
    print(f"matched_sources={stats.matched_source_count}")
    print(f"planned_buckets={stats.planned_bucket_count}")
    print(f"total_codepoints={stats.total_codepoint_count}")
    print(f"fallback_codepoints={stats.fallback_codepoint_count}")
    print(f"empty_buckets={stats.empty_bucket_count}")
    print(f"overlap_dropped={stats.overlap_dropped}")
    print(f"max_bucket_codepoints={stats.max_bucket_codepoint_count}")
    print(f"estimated_files={','.join(stats.estimated_files)}")
    print(f"assets={asset_count}")
    if warning_count:
        print(f"warnings={warning_count}")


def _version_text() -> str:
    try:
        package_version = version("font-splitter")
    except PackageNotFoundError:
        package_version = "0.0.0"
    return f"font-splitter {package_version}"


if __name__ == "__main__":
    raise SystemExit(main())
