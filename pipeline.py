"""LangGraph pipeline for confirm_rule.md: Lead -> Researcher -> Fact-checker -> Lead.

Each candidate is one graph run, recorded in LangSmith as "claim C-0X".

    .venv/bin/python pipeline.py          # every candidate; writes summary.json and results.md if the safety checks pass
    .venv/bin/python pipeline.py C-05     # one or more candidates; prints only, writes no files
"""

import csv
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TypedDict

from langchain_core.tracers.langchain import wait_for_all_tracers
from langgraph.graph import END, START, StateGraph
from langsmith import Client
from langsmith.wrappers import wrap_openai

from check_claim import DATA_FILE, ROOT, RULE_FILE, SNAPSHOT_FILE, candidate_pages, yes_no
from openrouter_client import DEFAULT_MODEL, get_client
from tests.test_safety import SUMMARY_FILE, check_confirmed, check_rejected, is_official_aws_url

RESULTS_FILE = ROOT / "results.md"
BLOCKED_FILE = ROOT / "summary.blocked.json"

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
    check1 = bool(page and is_official_aws_url(page["url"]))
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


def load_rows(path: Path = DATA_FILE) -> list:
    with open(path, newline="", encoding="utf-8") as f:
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


def add_trace_links(results: list) -> None:
    """Looks up each run's LangSmith URL. Call after wait_for_all_tracers()."""
    ls = Client()
    for r in results:
        try:
            r["trace_link"] = ls.get_run_url(run=ls.read_run(r["run_id"]))
        except Exception:
            r["trace_link"] = None


def full_reason(r: dict) -> str:
    if all(r["checks"]):
        return "All three checks passed."
    return f'Check {r["checks"].index(False) + 1} failed: {r["reason"]}'


def lead_summary(results: list) -> dict:
    """Final lead step: gathers every result into a confirmed list and a rejected list."""
    confirmed, rejected = [], []
    for r in results:
        if all(r["checks"]):
            confirmed.append({
                "candidate_id": r["row"]["candidate_id"],
                "source_url": r["url"],
                "quote": r["quote"],
                "trace_link": r["trace_link"],
            })
        else:
            rejected.append({
                "candidate_id": r["row"]["candidate_id"],
                "reason": full_reason(r),
                "trace_link": r["trace_link"],
            })
    return {"confirmed": confirmed, "rejected": rejected}


def safety_checks(summary: dict) -> Optional[str]:
    """Runs tests/test_safety.py's checks on both lists. Returns why they failed, or None if both pass."""
    try:
        check_confirmed(summary["confirmed"])
        check_rejected(summary["rejected"])
    except AssertionError as error:
        return str(error)
    return None


def print_summary(summary: dict) -> None:
    def short(text: str, limit: int = 100) -> str:
        text = " / ".join(" ".join(line.split()) for line in (text or "").splitlines() if line.strip())
        return text if len(text) <= limit else text[: limit - 3] + "..."

    print(f"Confirmed ({len(summary['confirmed'])}):")
    for item in summary["confirmed"]:
        print(f"  {item['candidate_id']}  {item['source_url']}")
        print(f"         \"{short(item['quote'])}\"")
        print(f"         trace: {item['trace_link'] or 'not recorded'}")
    print(f"Rejected ({len(summary['rejected'])}):")
    for item in summary["rejected"]:
        print(f"  {item['candidate_id']}  {short(item['reason'])}")
        print(f"         trace: {item['trace_link'] or 'not recorded'}")


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def write_results(results: list, run_at: str) -> None:
    """results.md: one row per candidate, with a link to its LangSmith trace."""
    lines = [
        "# Results",
        "",
        f"Each claim was checked by `pipeline.py` (Lead, Researcher, Fact-checker) against "
        f"`data/aws_official_source_snapshot.json` using `{DEFAULT_MODEL}`, following `confirm_rule.md`.",
        "",
        f"Run: {run_at}. `summary.json` comes from the same run. Both are written only after the safety checks pass.",
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
        trace = f"[trace]({r['trace_link']})" if r.get("trace_link") else "not recorded"
        lines.append(
            f"| {row['candidate_id']} | {cell(row['claim_text'])} | {verdict} | {cell(source)} | {cell(full_reason(r))} | {trace} |"
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


def main(wanted: set) -> dict:
    """Runs each candidate through the graph, then the final lead step. Returns both lists."""
    rows = load_rows()
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
    add_trace_links(results)
    return finish(results, full_run=not wanted)


def finish(results: list, full_run: bool) -> dict:
    """Builds both lists and runs the safety checks before anything is written or printed.

    Passing full run: writes summary.json and results.md from this one run, then the briefing.
    Passing partial run (some candidate ids only): writes no files, so both stay from one full run.
    Failing run: writes neither file, saves the lists to summary.blocked.json and exits with an error.
    """
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = {"run_at": run_at, "model": DEFAULT_MODEL, **lead_summary(results)}

    failure = safety_checks(summary)
    if failure:
        BLOCKED_FILE.write_text(json.dumps({**summary, "safety_check_failed": failure}, indent=2) + "\n",
                                encoding="utf-8")
        sys.exit(f"Safety check failed: {failure}\n"
                 f"Nothing was written to {RESULTS_FILE.name} or {SUMMARY_FILE.name} and no briefing was built. "
                 f"The blocked lists are in {BLOCKED_FILE.name}.")

    if full_run:
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        write_results(results, run_at)
        BLOCKED_FILE.unlink(missing_ok=True)
        print(f"Safety checks passed. Wrote {SUMMARY_FILE.name} and {RESULTS_FILE.name} (run {run_at}).\n")
    else:
        print("Safety checks passed. Partial run, so no files were written.\n")
    print_summary(summary)
    return summary


if __name__ == "__main__":
    main(set(sys.argv[1:]))
