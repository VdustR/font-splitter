from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tinycss2

from .ranges import parse_unicode_range_list
from .sources import RangeBucket


class CssAmbiguityError(ValueError):
    pass


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
            descriptors[declaration.lower_name] = (
                tinycss2.serialize(declaration.value).strip().strip("'\"")
            )

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
    descriptor_groups = {_descriptor_group(rule) for rule in rules}

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

    filtered_groups = {_descriptor_group(rule) for rule in filtered}
    if len(filtered_groups) > 1:
        raise CssAmbiguityError("CSS filters still match multiple font descriptor groups")
    return filtered


def _descriptor_group(rule: _FontFaceRule) -> tuple[str | None, str | None, str | None, str | None]:
    return (
        rule.descriptors.get("font-family"),
        rule.descriptors.get("font-weight"),
        rule.descriptors.get("font-style"),
        rule.descriptors.get("font-stretch"),
    )
