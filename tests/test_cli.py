import logging
import subprocess
import sys

from fontTools import subset

from font_splitter.cli import main
from tests.helpers import build_test_font


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "font_splitter.cli", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_cli_generates_woff2_and_css(tmp_path):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    completed = run_cli(
        str(font_path),
        "--output",
        str(output_dir),
        "--flavor",
        "woff2",
        "--max-codepoints",
        "-",
        "--local-src",
        "none",
    )
    assert "planned_buckets=" in completed.stdout
    assert (output_dir / "POC-Test.Basic-Latin.woff2").exists()
    assert (output_dir / "POC-Test.css").exists()


def test_cli_accepts_v1_flags_and_quiet_aliases(tmp_path):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    completed = run_cli(
        str(font_path),
        "--output",
        str(output_dir),
        "--chunk",
        "-",
        "--family",
        "CLI Test",
        "--italic",
        "--weight",
        "700",
        "--quiet",
    )

    assert completed.stdout == ""
    css = (output_dir / "CLI-Test.css").read_text(encoding="utf-8")
    assert "font-style: italic;" in css
    assert "font-weight: 700;" in css
    assert (output_dir / "CLI-Test.Basic-Latin.woff2").exists()

    output_dir_alias = tmp_path / "alias-out"
    completed_alias = run_cli(
        str(font_path),
        "--output",
        str(output_dir_alias),
        "--quite",
    )
    assert completed_alias.stdout == ""


def test_cli_dry_run_does_not_write_assets(tmp_path):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    completed = run_cli(str(font_path), "--output", str(output_dir), "--dry")

    assert "planned_buckets=" in completed.stdout
    assert "total_codepoints=" in completed.stdout
    assert "estimated_files=" in completed.stdout
    assert not output_dir.exists()


def test_cli_dry_run_does_not_subset(tmp_path, monkeypatch):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    def fail_subset(self, font):
        raise AssertionError("dry run must not subset")

    monkeypatch.setattr(subset.Subsetter, "subset", fail_subset)

    main([str(font_path), "--output", str(output_dir), "--dry"])

    assert not output_dir.exists()


def test_cli_font_css_source_without_fallback(tmp_path):
    font_path = tmp_path / "input.ttf"
    css_path = tmp_path / "template.css"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())
    css_path.write_text(
        """
@font-face {
  font-family: 'POC Test';
  font-style: normal;
  font-weight: 400;
  unicode-range: U+0041;
}
""",
        encoding="utf-8",
    )

    run_cli(
        str(font_path),
        "--output",
        str(output_dir),
        "--source",
        f"font-css:{css_path}",
        "--font-css-family",
        "POC Test",
        "--font-css-weight",
        "400",
        "--no-fallback",
        "--local-src",
        "none",
    )

    assert (output_dir / "POC-Test.font-css-001.woff2").exists()
    assert not (output_dir / "POC-Test.Basic-Latin.woff2").exists()


def test_cli_explicit_unicode_blocks_does_not_duplicate_fallback(tmp_path):
    font_path = tmp_path / "input.ttf"
    font_path.write_bytes(build_test_font())

    completed = run_cli(str(font_path), "--source", "unicode-blocks", "--dry")

    assert "planned_buckets=1" in completed.stdout
    assert "fallback_codepoints=0" in completed.stdout


def test_cli_output_style_and_stretch_overrides(tmp_path):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())

    run_cli(
        str(font_path),
        "--output",
        str(output_dir),
        "--style",
        "oblique",
        "--stretch",
        "condensed",
    )

    css = (output_dir / "POC-Test.css").read_text(encoding="utf-8")
    assert "font-style: oblique;" in css
    assert "font-stretch: condensed;" in css


def test_cli_prints_warning_count(tmp_path, monkeypatch, capsys):
    font_path = tmp_path / "input.ttf"
    output_dir = tmp_path / "out"
    font_path.write_bytes(build_test_font())
    original_subset = subset.Subsetter.subset

    def subset_with_warning(self, font):
        logging.getLogger("fontTools.subset").warning("synthetic CLI warning")
        return original_subset(self, font)

    monkeypatch.setattr(subset.Subsetter, "subset", subset_with_warning)

    main([str(font_path), "--output", str(output_dir), "--chunk", "-"])

    captured = capsys.readouterr()
    assert "warnings=1" in captured.out
