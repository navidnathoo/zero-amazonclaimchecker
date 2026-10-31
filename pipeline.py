"""LangGraph pipeline for confirm_rule.md: Lead -> Researcher -> Fact-checker -> Lead.

Each candidate is one graph run, recorded in LangSmith as "claim C-0X".

    .venv/bin/python pipeline.py          # every candidate in the CSV, then writes results.md
    .venv/bin/python pipeline.py C-05     # one or more candidates (results.md left as is)
"""

import csv
import json
import re
import sys
import uuid
from typing import List, Optional, TypedDict

from langchain_core.tracers.langchain import wait_for_all_tracers
from langgraph.graph import END, START, StateGraph
from langsmith import Client
from langsmith.wrappers import wrap_openai

from check_claim import DATA_FILE, ROOT, RULE_FILE, SNAPSHOT_FILE, candidate_pages, yes_no
from openrouter_client import DEFAULT_MODEL, get_client

RESULTS_FILE = ROOT / "results.md"

PAGES = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
PAGES_BY_ID = {p["page_id"]: p for p in PAGES}
RULE = RULE_FILE.read_text(encoding="utf-8")
client = wrap_openai(get_client())


class ClaimState(TypedDict, total=False):
    row: dict
    page_id: Optional[str]
    url: Optional[str]
    quote: Optional[str]
    checks: List[bool]
    facts: List[dict]
    reason: str
    verdict: str


def ask_json(role: str, prompt: str) -> dict:
    """One model call that must answer with a JSON object."""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": f"{RULE}\n\nYou are the {role}. Reply with JSON only, no other text."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
    )
    text = response.choices[0].message.content or ""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def lead(state: ClaimState) -> ClaimState:
    """Hands the claim out, then writes the verdict once the fact-checker has answered."""
    if "checks" not in state:
        return {}
    if all(state["checks"]):
        return {"verdict": "confirmed"}
    failed = state["checks"].index(False) + 1
    return {"verdict": f'rejected. Reason: "Check {failed} failed: {state["reason"]}"'}


def route_from_lead(state: ClaimState) -> str:
    return END if "verdict" in state else "researcher"


def researcher(state: ClaimState) -> ClaimState:
    """Finds the claim's page in the snapshot and copies the exact sentences, or reports no match."""
    row = state["row"]
    shortlist = candidate_pages(row, PAGES)
    if not shortlist:
        return {"page_id": None, "url": None, "quote": None}
    sources = "\n\n".join(
        f"[{p['page_id']}] {p['url']}\nTitle: {p['title']}\nPublished: {p['published_date']}\n{p['body_text']}"
        for p in shortlist
    )
    answer = ask_json(
        "researcher",
        f"Claim: {row['claim_text']}\n\nOfficial AWS pages from the snapshot:\n\n{sources}\n\n"
        "Pick the page that best covers this claim and copy every body sentence that bears on it, word for word. "
        "(The page title is added for you.) If no page covers the claim, use null and an empty list.\n"
        '{"page_id": "<page id or null>", "sentences": ["<exact title or sentence>", "..."]}',
    )
    page = PAGES_BY_ID.get(answer.get("page_id") or "")
    sentences = [s.strip() for s in answer.get("sentences") or [] if isinstance(s, str) and s.strip()]
    # The title is part of the page and can state facts the body leaves out, so it always goes first.
    if page and sentences and page["title"] not in sentences:
        sentences.insert(0, page["title"])
    return {
        "page_id": page["page_id"] if page else None,
        "url": page["url"] if page else None,
        "quote": "\n".join(sentences) or None,
    }


def on_page(piece: str, page: dict) -> bool:
    """True if this piece is copied exactly from the page's body or title."""
    return piece in page["body_text"] or piece.rstrip(".") in page["title"]


def fact_checker(state: ClaimState) -> ClaimState:
    """Answers the three checks. Checks 1 and 2 are exact tests; check 3 asks the model."""
    page = PAGES_BY_ID.get(state.get("page_id") or "")
    quote = state.get("quote") or ""
    check1 = bool(page and page["url"].startswith("https://aws.amazon.com/"))
    if not check1:
        return {"checks": [False, False, False],
                "reason": "no source page on aws.amazon.com in the snapshot matches this claim."}
    pieces = [s for line in quote.splitlines() for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]
    check2 = bool(pieces) and all(on_page(s, page) for s in pieces)
    if not check2:
        return {"checks": [True, False, False],
                "reason": "the sentences are not copied exactly from the source page."}
    answer = ask_json(
        "fact-checker",
        f"Claim: {state['row']['claim_text']}\n\nSource: {page['url']}\nSentences copied from it:\n{quote}\n\n"
        "Split the claim into every separate fact it states (service, what it does, launch stage, "
        "Regions, scale, dates and so on). For each fact, say whether the copied sentences state it. "
        "Use only the copied sentences, not outside knowledge. If unsure, it is not supported. "
        "For a supported fact, give the words from the copied sentences that back it, copied exactly, "
        'and say whether they state the fact in the same words ("exact") or in different words that mean '
        'the same thing ("same meaning"). '
        "For an unsupported fact, say in a few words what the sentences say instead.\n"
        '{"facts": [{"fact": "<fact from the claim>", "supported": true or false, '
        '"evidence": "<exact words from the copied sentences, or null>", '
        '"match": "exact" or "same meaning" or null, "note": "<short note if unsupported, or null>"}]}',
    )
    facts = []
    for f in answer.get("facts") or []:
        evidence = (f.get("evidence") or "").strip()
        # A fact only counts as supported if its evidence really is in the copied sentences.
        supported = f.get("supported") is True and bool(evidence) and evidence in quote
        facts.append({
            "fact": (f.get("fact") or "").rstrip("."),
            "supported": supported,
            "evidence": evidence if supported else None,
            "match": (f.get("match") or "same meaning") if supported else None,
            "note": None if supported else (f.get("note") or "not stated in the copied sentences"),
        })
    unsupported = [f for f in facts if not f["supported"]]
    check3 = bool(facts) and not unsupported
    if not facts:
        reason = "the fact-checker did not list the claim's facts."
    elif unsupported:
        reason = "; ".join(f"'{f['fact']}' is not backed ({f['note'].rstrip('.')})" for f in unsupported) + "."
    else:
        reason = "every fact is backed by the copied sentences."
    return {"checks": [True, True, check3], "facts": facts, "reason": reason}


builder = StateGraph(ClaimState)
builder.add_node("lead", lead)
builder.add_node("researcher", researcher)
builder.add_node("fact_checker", fact_checker)
builder.add_edge(START, "lead")
builder.add_conditional_edges("lead", route_from_lead, ["researcher", END])
builder.add_edge("researcher", "fact_checker")
builder.add_edge("fact_checker", "lead")
graph = builder.compile()


def load_rows() -> list:
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(row: dict) -> ClaimState:
    candidate_id = row["candidate_id"]
    run_id = uuid.uuid4()
    result = graph.invoke(
        {"row": row},
        config={
            "run_id": run_id,
            "run_name": f"claim {candidate_id}",
            "metadata": {"candidate_id": candidate_id, "claim_type": row["claim_type"]},
            "tags": ["pipeline", candidate_id],
        },
    )
    return {**result, "run_id": run_id}


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def write_results(results: list) -> None:
    """results.md: one row per candidate, with a link to its LangSmith trace."""
    ls = Client()
    lines = [
        "# Results",
        "",
        f"Each claim was checked by `pipeline.py` (Lead, Researcher, Fact-checker) against "
        f"`data/aws_official_source_snapshot.json` using `{DEFAULT_MODEL}`, following `confirm_rule.md`.",
        "",
        "| Candidate | Claim | Verdict | Source URL and quote | Reason | Trace |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        row = r["row"]
        verdict = "confirmed" if all(r["checks"]) else "rejected"
        if r.get("url"):
            source = f'{r["url"]}<br>"{r.get("quote") or ""}"'
        else:
            source = "no match"
        reason = r["reason"] if verdict == "rejected" else "All three checks passed."
        if verdict == "rejected":
            reason = f'Check {r["checks"].index(False) + 1} failed: {reason}'
        try:
            trace = f"[trace]({ls.get_run_url(run=ls.read_run(r['run_id']))})"
        except Exception:
            trace = "not recorded"
        lines.append(
            f"| {row['candidate_id']} | {cell(row['claim_text'])} | {verdict} | {cell(source)} | {cell(reason)} | {trace} |"
        )

    lines += ["", "## Every fact, checked against the quote", ""]
    for r in results:
        lines += [f"### {r['row']['candidate_id']}", ""]
        if not r.get("facts"):
            lines += ["No facts checked: the claim failed before check 3.", ""]
            continue
        lines += ["| Fact in the claim | Backed? | Words from the quote, or what it says instead |", "|---|---|---|"]
        for f in r["facts"]:
            if f["supported"]:
                backed = "yes" if f["match"] == "exact" else "yes (same meaning)"
                lines.append(f'| {cell(f["fact"])} | {backed} | "{cell(f["evidence"])}" |')
            else:
                lines.append(f'| {cell(f["fact"])} | **no** | {cell(f["note"])} |')
        lines.append("")
    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    rows = load_rows()
    wanted = set(sys.argv[1:])
    if wanted:
        rows = [r for r in rows if r["candidate_id"] in wanted]
    results = []
    for row in rows:
        result = run(row)
        results.append(result)
        c1, c2, c3 = result["checks"]
        print(f"{row['candidate_id']}: {row['claim_text']}")
        print(f"  1. Source page on aws.amazon.com: {yes_no(c1)}, {result.get('url') or 'none'}")
        print(f"  2. Sentences copied word for word: {yes_no(c2)}")
        print(f"  3. Sentences back every fact: {yes_no(c3)}")
        print(f"  Verdict: {result['verdict']}\n")
    wait_for_all_tracers()
    if not wanted:
        write_results(results)
        print(f"Wrote {RESULTS_FILE.name}")
