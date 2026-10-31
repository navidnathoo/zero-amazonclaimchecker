"""Safety checks on the confirmed and rejected lists from pipeline.py.

pipeline.py calls check_confirmed() and check_rejected() before it builds the briefing,
and stops if either fails. pytest runs the same checks on the lists from the latest
pipeline run, which pipeline.py saves to summary.json:

    .venv/bin/python -m pytest tests/test_safety.py
"""

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

SUMMARY_FILE = Path(__file__).resolve().parent.parent / "summary.json"


def is_official_aws_url(url: str) -> bool:
    """True only for an https page whose host is exactly aws.amazon.com.

    "aws.amazon.com" appearing somewhere in the URL is not enough: it rules out hosts like
    aws.amazon.com.example.net, paths like example.com/aws.amazon.com/, and tricks like
    https://aws.amazon.com@example.com/ (where the real host is example.com).
    """
    try:
        parts = urlsplit(url or "")
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.hostname == "aws.amazon.com"
        and parts.username is None
        and port in (None, 443)
    )


def check_confirmed(confirmed: list) -> None:
    """Every confirmed item has a source_url on aws.amazon.com and a non-empty quote."""
    for item in confirmed:
        name = item.get("candidate_id", "a confirmed item")
        assert is_official_aws_url(item.get("source_url")), f"{name}: source_url is not on aws.amazon.com"
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


@pytest.mark.parametrize("url", [
    "https://aws.amazon.com.example.net/news/s3-vectors-ga",
    "https://myblog.example.com/aws.amazon.com/s3-vectors-ga",
    "https://www.reddit.com/r/aws/comments/abc/?via=aws.amazon.com",
    "https://aws.amazon.com@evil.example.com/s3-vectors",
    "http://aws.amazon.com/about-aws/whats-new/",
])
def test_lookalike_urls_are_not_official(url):
    assert not is_official_aws_url(url)
    with pytest.raises(AssertionError, match="not on aws.amazon.com"):
        check_confirmed([{"candidate_id": "X", "source_url": url, "quote": "q"}])


def test_official_url_is_accepted():
    assert is_official_aws_url("https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/")
