"""load_snapshot(): the refresh file, when present, replaces or adds pages for the researcher.

Uses temporary files, so no made-up pages go into data/.
"""

import json

import pytest

import check_claim


def page(page_id: str, url: str, body: str) -> dict:
    return {"page_id": page_id, "url": url, "title": f"Title {page_id}", "service_name": "S",
            "published_date": "2025-12-01", "body_text": body}


@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.setattr(check_claim, "ROOT", tmp_path)
    monkeypatch.setattr(check_claim, "SNAPSHOT_FILE", tmp_path / "snapshot.json")
    monkeypatch.setattr(check_claim, "REFRESH_FILE", tmp_path / "refresh.json")
    (tmp_path / "snapshot.json").write_text(json.dumps([
        page("A", "https://aws.amazon.com/a/", "old A"),
        page("B", "https://aws.amazon.com/b/", "old B"),
    ]))
    return tmp_path


def test_without_refresh_only_the_snapshot_is_loaded(files):
    pages = check_claim.load_snapshot()
    assert [p["page_id"] for p in pages] == ["A", "B"]
    assert {p["snapshot_file"] for p in pages} == {"snapshot.json"}


def test_refresh_replaces_matching_pages_and_adds_new_ones(files):
    (files / "refresh.json").write_text(json.dumps([
        page("A2", "https://aws.amazon.com/a/", "new A"),   # same url as A: replaces it
        page("C", "https://aws.amazon.com/c/", "new C"),    # new page: added
    ]))
    pages = {p["page_id"]: p for p in check_claim.load_snapshot()}
    assert set(pages) == {"B", "A2", "C"}
    assert pages["A2"]["body_text"] == "new A" and pages["A2"]["snapshot_file"] == "refresh.json"
    assert pages["B"]["snapshot_file"] == "snapshot.json"


def test_refresh_page_missing_a_field_stops_the_run(files):
    bad = page("C", "https://aws.amazon.com/c/", "x")
    del bad["body_text"]
    (files / "refresh.json").write_text(json.dumps([bad]))
    with pytest.raises(SystemExit, match="missing body_text"):
        check_claim.load_snapshot()
