"""Client-side tools: tools that run on *your* machine.

Web search and web fetch are server tools - they run on Anthropic's
infrastructure, so there is nothing to implement for them here. The only
local tool is `save_report`, which writes the finished report to disk.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REPORTS_DIR = Path("reports")
MAX_FILENAME_LENGTH = 80

SAVE_REPORT_TOOL: dict[str, Any] = {
    "name": "save_report",
    "description": (
        "Save the finished research report as a Markdown file in the local "
        "reports/ folder. Call this once, after the research is complete, with "
        "the full report (including a Sources section with URLs). Returns the "
        "path of the saved file."
    ),
    # Reports can be long; stream the input as it is generated instead of
    # waiting for the whole parameter to be buffered server-side.
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Short descriptive file name, e.g. 'electric-cars-indonesia'. No folders.",
            },
            "content": {
                "type": "string",
                "description": "The complete report in Markdown.",
            },
        },
        "required": ["filename", "content"],
        "additionalProperties": False,
    },
}


def slugify(name: str) -> str:
    """Turn any model-supplied name into a safe, flat file stem.

    Removes folders, `..`, drive letters and odd characters so the model can
    never write outside the reports directory.
    """
    stem = Path(name.replace("\\", "/")).name
    stem = re.sub(r"\.md$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-_").lower()
    return stem[:MAX_FILENAME_LENGTH].rstrip("-_") or "report"


def save_report(filename: str, content: str, reports_dir: Path = REPORTS_DIR) -> Path:
    """Write the report to `reports_dir/<slug>.md` without overwriting old ones."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(filename)
    target = reports_dir / f"{stem}.md"
    counter = 2
    while target.exists():
        target = reports_dir / f"{stem}-{counter}.md"
        counter += 1
    target.write_text(content, encoding="utf-8")
    return target


def validate_save_report_input(args: Any) -> str | None:
    """Return an error message if the tool input is malformed, else None.

    With eager input streaming the API does not validate tool inputs for us,
    so we check the shape ourselves before running anything.
    """
    if not isinstance(args, dict):
        return "input must be a JSON object"
    extra = set(args) - {"filename", "content"}
    if extra:
        return f"unexpected fields: {sorted(extra)}"
    if not isinstance(args.get("filename"), str) or not args["filename"].strip():
        return "'filename' must be a non-empty string"
    if not isinstance(args.get("content"), str) or not args["content"].strip():
        return "'content' must be a non-empty string"
    return None


def run_client_tool(name: str, args: Any, reports_dir: Path = REPORTS_DIR) -> tuple[str, bool]:
    """Execute a client tool. Returns (result_text, is_error)."""
    if name != "save_report":
        return f"unknown tool: {name}", True
    error = validate_save_report_input(args)
    if error:
        return f"invalid input: {error}", True
    try:
        path = save_report(args["filename"], args["content"], reports_dir)
    except OSError as exc:
        return f"could not save report: {exc}", True
    return f"Report saved to {path.as_posix()}", False
