import pytest

from font_splitter.planner import PlannedBucket, plan_buckets
from font_splitter.sources import RangeBucket
from font_splitter.unicode_blocks import UnicodeBlockSource


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
    assert plan.empty_dropped == 0
    assert plan.matched_source_count == 2
    assert plan.fallback_codepoint_count == 0
    assert plan.total_codepoint_count == 3
    assert plan.max_bucket_codepoint_count == 2


def test_fallback_remaining_to_unicode_blocks():
    cmap = {0x41, 0x42, 0x2600}
    first = StaticSource([RangeBucket("latin", "latin", {0x41})])
    plan = plan_buckets(cmap, [first], fallback=UnicodeBlockSource(), max_codepoints=10)
    assert [(bucket.id, bucket.codepoints) for bucket in plan.buckets] == [
        ("latin", {0x41}),
        ("Basic-Latin", {0x42}),
        ("Miscellaneous-Symbols", {0x2600}),
    ]
    assert plan.matched_source_count == 1
    assert plan.fallback_codepoint_count == 2
    assert plan.total_codepoint_count == 3
    assert plan.max_bucket_codepoint_count == 1


def test_unicode_block_source_uses_fonttools_block_data():
    source = UnicodeBlockSource()
    bucket_by_id = {bucket.id: bucket for bucket in source.buckets()}

    assert bucket_by_id["Latin-Extended-A"].codepoints == set(range(0x0100, 0x0180))
    assert "No-Block" not in bucket_by_id


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


def test_reject_non_positive_max_codepoints():
    with pytest.raises(ValueError, match="max_codepoints must be positive"):
        plan_buckets({0x41}, [], fallback=None, max_codepoints=0)
