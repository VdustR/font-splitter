from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .sources import RangeSource


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
    matched_source_count: int
    fallback_codepoint_count: int
    total_codepoint_count: int
    max_bucket_codepoint_count: int


def plan_buckets(
    cmap_codepoints: Iterable[int],
    sources: list[RangeSource],
    *,
    fallback: RangeSource | None,
    max_codepoints: int | None,
) -> Plan:
    if max_codepoints is not None and max_codepoints < 1:
        raise ValueError("max_codepoints must be positive or None")

    available = set(cmap_codepoints)
    assigned: set[int] = set()
    buckets: list[PlannedBucket] = []
    overlap_dropped = 0
    empty_dropped = 0
    matched_sources: set[int] = set()
    fallback_codepoint_count = 0

    source_entries = [
        *[(index, source, False) for index, source in enumerate(sources)],
        *([(-1, fallback, True)] if fallback is not None else []),
    ]
    for source_index, source, is_fallback in source_entries:
        for candidate in source.buckets():
            in_font = candidate.codepoints & available
            overlap = in_font & assigned
            current = in_font - assigned
            overlap_dropped += len(overlap)
            if not current:
                empty_dropped += 1
                continue
            if is_fallback:
                fallback_codepoint_count += len(current)
            else:
                matched_sources.add(source_index)
            assigned.update(current)
            buckets.extend(_split_bucket(candidate.id, candidate.label, current, max_codepoints))

    return Plan(
        buckets=buckets,
        overlap_dropped=overlap_dropped,
        empty_dropped=empty_dropped,
        matched_source_count=len(matched_sources),
        fallback_codepoint_count=fallback_codepoint_count,
        total_codepoint_count=sum(len(bucket.codepoints) for bucket in buckets),
        max_bucket_codepoint_count=max((len(bucket.codepoints) for bucket in buckets), default=0),
    )


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
    width = max(3, len(str(len(chunks))))
    return [
        PlannedBucket(f"{bucket_id}-{index:0{width}d}", label, set(chunk))
        for index, chunk in enumerate(chunks, start=1)
    ]
