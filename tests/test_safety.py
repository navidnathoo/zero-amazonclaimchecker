"""Safety checks on the confirmed and rejected lists from pipeline.py.

pipeline.py calls check_confirmed() and check_rejected() before it builds the briefing,
and stops if either fails. pytest runs the same checks on the lists from the latest
pipeline run, which pipeline.py saves to summary.json:

    .venv/bin/python -m pytest tests/test_safety.py
"""

import json
from pathlib import Path

import pytest

SUMMARY_FILE = Path(__file__).resolve().parent.parent / "summary.json"


def check_confirmed(confirmed: list) -> None:
    """Every confirmed item has a source_url on aws.amazon.com and a non-empty quote."""
    for item in confirmed:
        name = item.get("candidate_id", "a confirmed item")
        assert "aws.amazon.com" in (item.get("source_url") or ""), f"{name}: source_url is not on aws.amazon.com"
        assert (item.get("quote") or "").strip(), f"{name}: quote is empty"


def check_rejected(rejected: list) -> None:
    """Every rejected item has a non-empty reason."""
    for item in rejected:
        name = item.get("candidate_id", "a rejected item")
        assert (item.get("reason") or "").strip(), f"{name}: reason is empty"


@pytest.fixture
def summary() -> dict:
    if not SUMMARY_FILE.exists():
        pytest.skip("No summary.json yet. Run pipeline.py first.")
    return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))


def test_confirmed_items_have_aws_source_and_quote(summary):
    check_confirmed(summary["confirmed"])


def test_rejected_items_have_reason(summary):
    check_rejected(summary["rejected"])
