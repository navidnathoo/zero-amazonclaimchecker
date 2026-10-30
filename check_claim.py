"""Check one candidate claim against the AWS source snapshot, traced in LangSmith.

The model picks a page and a quote from the snapshot. The script itself checks that
the page is on aws.amazon.com (check 1) and that the quote is copied exactly from it
(check 2). The model judges whether the quote backs every fact in the claim (check 3).
"""

import csv
import json
import re
import sys
from pathlib import Path

from langsmith import traceable
from langsmith.wrappers import wrap_openai

from openrouter_client import DEFAULT_MODEL, get_client

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "aws_reinvent_candidate_items.csv"
SNAPSHOT_FILE = ROOT / "data" / "aws_official_source_snapshot.json"
RULE_FILE = ROOT / "confirm_rule.md"
QUESTION = "Is this a real AWS launch? Answer yes or no, and name the page that proves it."
TOP_PAGES = 5

STOPWORDS = {
    "a", "an", "and", "are", "at", "aws", "amazon", "by", "for", "in", "is", "it",
    "now", "of", "on", "the", "to", "will", "with", "you", "all", "lets",
}


def load_row(candidate_id: str) -> dict:
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["candidate_id"] == candidate_id:
                return row
    sys.exit(f"No row with candidate_id {candidate_id} in {DATA_FILE}")


def words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def candidate_pages(row: dict, pages: list) -> list:
    """The snapshot pages that share the most words with the claim."""
    claim_words = words(row["claim_text"] + " " + row["claimed_service"])
    scored = [
        (len(claim_words & words(p["title"] + " " + p["service_name"] + " " + p["body_text"])), p)
        for p in pages
    ]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: s[0], reverse=True)
    return [p for _, p in scored[:TOP_PAGES]]


@traceable(name="check_claim")
def check_claim(row: dict) -> dict:
    pages = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    by_id = {p["page_id"]: p for p in pages}
    shortlist = candidate_pages(row, pages)

    sources = "\n\n".join(
        f"[{p['page_id']}] {p['url']}\nTitle: {p['title']}\nPublished: {p['published_date']}\n{p['body_text']}"
        for p in shortlist
    ) or "(no matching pages)"
    prompt = (
        f"Claim: {row['claim_text']}\n\n{QUESTION}\n\n"
        f"Use only these official AWS pages:\n\n{sources}"
    )
    system = (
        RULE_FILE.read_text(encoding="utf-8")
        + "\n\nFor this run, reply with JSON only instead of the answer format above, no other text:\n"
        '{"page_id": "<id of the best page, or null>", '
        '"quote": "<sentence(s) copied exactly from that page, or null>", '
        '"backs_every_fact": true or false, '
        '"reason": "<one line>"}'
    )
    client = wrap_openai(get_client())
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
    )
    text = response.choices[0].message.content or ""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    answer = json.loads(match.group(0)) if match else {}

    page = by_id.get(answer.get("page_id") or "")
    quote = (answer.get("quote") or "").strip()
    check1 = bool(page and page["url"].startswith("https://aws.amazon.com/"))
    check2 = bool(check1 and quote and quote in page["body_text"])
    check3 = bool(check2 and answer.get("backs_every_fact") is True)

    if not check1:
        verdict = "REJECTED: no source page on aws.amazon.com in the snapshot supports this claim."
    elif not check2:
        verdict = "REJECTED: the quote is not copied exactly from the source page."
    elif not check3:
        reason = re.sub(r"^(REJECTED:\s*)?(Check 3 failed\.\s*)?", "", answer.get("reason") or "")
        verdict = f"REJECTED: the quote does not back every fact. {reason}".strip()
    else:
        verdict = "CONFIRMED"

    return {
        "url": page["url"] if page else None,
        "quote": quote or None,
        "checks": [check1, check2, check3],
        "verdict": verdict,
    }


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    candidate_id = sys.argv[1] if len(sys.argv) > 1 else "C-02"
    row = load_row(candidate_id)
    result = check_claim(row, langsmith_extra={"metadata": {"candidate_id": candidate_id}})
    c1, c2, c3 = result["checks"]
    print(f"{candidate_id}: {row['claim_text']}\n")
    print(f"Check 1 (source page on aws.amazon.com): {yes_no(c1)}, {result['url'] or 'none'}")
    print(f'Check 2 (exact quote from that page): {yes_no(c2)}, "{result["quote"]}"' if result["quote"]
          else f"Check 2 (exact quote from that page): {yes_no(c2)}, none")
    print(f"Check 3 (quote backs every fact): {yes_no(c3)}")
    print(f"Verdict: {result['verdict']}")
