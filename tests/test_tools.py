"""Offline tests for the client tools (no API key or network needed)."""

from pathlib import Path

import pytest

from research_agent.tools import run_client_tool, save_report, slugify, validate_save_report_input


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Electric Cars Indonesia", "electric-cars-indonesia"),
        ("report.md", "report"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Windows\\system32\\evil", "evil"),
        ("///", "report"),
        ("", "report"),
        ("a" * 200, "a" * 80),
    ],
)
def test_slugify(raw: str, expected: str) -> None:
    assert slugify(raw) == expected


def test_save_report_stays_inside_reports_dir(tmp_path: Path) -> None:
    path = save_report("../outside", "# Hi", tmp_path)
    assert path.parent == tmp_path
    assert path.read_text(encoding="utf-8") == "# Hi"


def test_save_report_does_not_overwrite(tmp_path: Path) -> None:
    first = save_report("topic", "one", tmp_path)
    second = save_report("topic", "two", tmp_path)
    assert first.name == "topic.md"
    assert second.name == "topic-2.md"
    assert first.read_text(encoding="utf-8") == "one"


@pytest.mark.parametrize(
    "args",
    [
        None,
        "not a dict",
        {"filename": "x"},
        {"content": "x"},
        {"filename": "", "content": "x"},
        {"filename": "x", "content": 5},
        {"filename": "x", "content": "y", "extra": 1},
    ],
)
def test_validate_rejects_bad_input(args: object) -> None:
    assert validate_save_report_input(args) is not None


def test_run_client_tool(tmp_path: Path) -> None:
    text, is_error = run_client_tool("save_report", {"filename": "ok", "content": "# Report"}, tmp_path)
    assert not is_error
    assert (tmp_path / "ok.md").exists()

    text, is_error = run_client_tool("save_report", {"filename": "ok"}, tmp_path)
    assert is_error and "invalid input" in text

    text, is_error = run_client_tool("delete_everything", {}, tmp_path)
    assert is_error
