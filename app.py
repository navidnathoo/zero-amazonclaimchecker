"""Local server for briefing.html: check one claim, and list the holdout claims' results.

    .venv/bin/python app.py              # then open http://127.0.0.1:8765
    .venv/bin/python app.py --holdout              # check every holdout claim; if the safety checks pass,
                                                   # save results, spotcheck.md and docs/index.html
    .venv/bin/python app.py --holdout --publish    # the same, and make the traces public for the published page

Claims go through pipeline.py's graph (Lead, Researcher, Fact-checker) and the same safety
checks. It only listens on this computer, because it uses the API keys in .env.
"""

import json
import sys
import uuid
import warnings
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

warnings.filterwarnings("ignore")

import pipeline  # noqa: E402
from langchain_core.tracers.langchain import wait_for_all_tracers  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
ROOT = Path(__file__).parent
PAGE = ROOT / "briefing.html"
HOLDOUT_FILE = ROOT / "data" / "aws_reinvent_candidate_items_holdout.csv"
HOLDOUT_RESULTS = ROOT / "data" / "holdout_results.json"
SPOTCHECK_FILE = ROOT / "spotcheck.md"
STATIC_PAGE = ROOT / "docs" / "index.html"
MAX_CLAIM_LENGTH = 1000


def without_title(quote: str, page: dict) -> str:
    """The page title is shown as the source link, so don't repeat it as the quote's first line."""
    lines = (quote or "").splitlines()
    if page and lines and lines[0].strip() == page["title"]:
        return "\n".join(lines[1:]).strip() or quote
    return quote


def check(claim: str) -> dict:
    """Checks one claim and returns what the page needs to show."""
    row = {
        "candidate_id": f"UI-{uuid.uuid4().hex[:6]}",
        "claim_text": claim,
        "claimed_service": "",
        "claim_type": "ui",
    }
    result = pipeline.run(row)
    wait_for_all_tracers()
    pipeline.add_trace_links([result])

    page = pipeline.PAGES_BY_ID.get(result.get("page_id") or "")
    verified = all(result["checks"])
    reason = pipeline.full_reason(result)

    # The same safety gate as the pipeline: never say "verified" without an official source and a quote.
    summary = pipeline.lead_summary([result])
    failure = pipeline.safety_checks(summary)
    if verified and failure:
        verified, reason = False, f"Safety check failed: {failure}"

    quote = without_title(result.get("quote"), page) if result["checks"][1] else None

    return {
        "verified": verified,
        "failed_check": None if verified or all(result["checks"]) else result["checks"].index(False) + 1,
        "reason": reason,
        "source": {
            "url": page["url"],
            "title": page["title"],
            "published": page["published_date"],
        } if page and result["checks"][0] else None,
        "quote": quote,
        "facts": result.get("facts") or [],
        "trace_link": result.get("trace_link"),
    }


def log(message: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] {message}", flush=True)


def build_holdout(publish: bool) -> None:
    """Checks every holdout claim, then runs the safety checks before anything is saved or built.

    Only if both checks pass: makes the traces public (with --publish), saves the results,
    writes spotcheck.md and builds the published page, docs/index.html.
    """
    if not HOLDOUT_FILE.exists():
        sys.exit(f"Missing {HOLDOUT_FILE.relative_to(ROOT)}. Add it, then run this again.")
    rows = []
    for n, row in enumerate(pipeline.load_rows(HOLDOUT_FILE), start=1):
        if not (row.get("claim_text") or "").strip():
            continue
        rows.append({**row,
                     "candidate_id": row.get("candidate_id") or f"H-{n:02d}",
                     "claimed_service": row.get("claimed_service") or "",
                     "claim_type": row.get("claim_type") or "holdout"})
    log(f"Holdout file: {HOLDOUT_FILE.relative_to(ROOT)} ({len(rows)} claims: {', '.join(r['candidate_id'] for r in rows)})")
    refreshed = sum(p["snapshot_file"] == str(pipeline.REFRESH_FILE.relative_to(ROOT)) for p in pipeline.PAGES)
    if pipeline.REFRESH_FILE.exists():
        log(f"Pages for the researcher: {len(pipeline.PAGES)} ({refreshed} from {pipeline.REFRESH_FILE.relative_to(ROOT)}, "
            f"the rest from {pipeline.SNAPSHOT_FILE.relative_to(ROOT)})")
    else:
        log(f"Pages for the researcher: {len(pipeline.PAGES)} from {pipeline.SNAPSHOT_FILE.relative_to(ROOT)}. "
            f"No refresh file ({pipeline.REFRESH_FILE.relative_to(ROOT)}), so launches after that capture can't be confirmed.")
    results = []
    for row in rows:
        log(f"Checking {row['candidate_id']}: {row['claim_text']}")
        result = pipeline.run(row)
        log(f"  {row['candidate_id']} verdict: {result['verdict']}")
        results.append(result)
    wait_for_all_tracers()
    pipeline.add_trace_links(results)

    summary = pipeline.lead_summary(results)
    failure = pipeline.safety_checks(summary)
    if failure:
        log(f"SAFETY CHECKS FAILED: {failure}")
        sys.exit("Nothing was saved and no page was built.")
    log(f"SAFETY CHECKS PASSED: {len(summary['confirmed'])} confirmed items have an aws.amazon.com source and a quote; "
        f"{len(summary['rejected'])} rejected items have a reason.")

    if publish:
        for r in results:
            if r.get("trace_link"):
                r["trace_link"] = pipeline.Client().share_run(str(r["run_id"]))
        log(f"Made {len(results)} traces public.")

    items = []
    for r in results:
        page = pipeline.PAGES_BY_ID.get(r.get("page_id") or "")
        confirmed = all(r["checks"])
        items.append({
            "candidate_id": r["row"]["candidate_id"],
            "claim": r["row"]["claim_text"],
            "verdict": "confirmed" if confirmed else "rejected",
            "source_url": r["url"] if confirmed else None,
            "source_title": page["title"] if confirmed and page else None,
            "published": page["published_date"] if confirmed and page else None,
            "quote": without_title(r["quote"], page) if confirmed else None,
            "full_quote": r["quote"] if confirmed else None,
            "page_id": r.get("page_id") if confirmed else None,
            "reason": None if confirmed else pipeline.full_reason(r),
            "trace_link": r.get("trace_link"),
        })
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    HOLDOUT_RESULTS.write_text(json.dumps({"run_at": run_at, "model": pipeline.DEFAULT_MODEL, "items": items},
                                          indent=2) + "\n", encoding="utf-8")
    log(f"Saved {len(items)} results to {HOLDOUT_RESULTS.relative_to(ROOT)}.")

    write_spotcheck(items, run_at)
    log(f"Wrote {SPOTCHECK_FILE.relative_to(ROOT)}.")

    build_static_page()
    log(f"BUILT PAGE: {STATIC_PAGE.relative_to(ROOT)} (holdout results embedded, no server needed).")


def write_spotcheck(items: list, run_at: str) -> None:
    """spotcheck.md: every confirmed holdout item, re-checked against the snapshot, with boxes for a person."""
    confirmed = [i for i in items if i["verdict"] == "confirmed"]
    lines = [
        "# Spot check: confirmed holdout claims",
        "",
        f"Holdout run of {run_at}. Each confirmed claim below was re-checked by code against the `body_text` of its "
        "page in the file named under it (the refresh snapshot when the page is in it). "
        "Open each source and tick or fail each box by hand.",
        "",
    ]
    if not confirmed:
        lines += ["No holdout claims were confirmed in this run, so there is nothing to spot check.", ""]
    for i in confirmed:
        page = pipeline.PAGES_BY_ID.get(i["page_id"] or "")
        sentences = [s for line in (i["full_quote"] or "").splitlines()
                     for s in pipeline.re.split(r"(?<=[.!?])\s+", line.strip()) if s]
        on_page = bool(page) and all(pipeline.on_page(s, page) for s in sentences)
        lines += [
            f"## {i['candidate_id']}",
            "",
            f"**Claim:** {i['claim']}",
            "",
            f"**Source:** [{i['source_title']}]({i['source_url']}) (published {i['published']})",
            "",
            f"**Checked against:** `{page['snapshot_file'] if page else 'page not found'}`, page `{i['page_id']}`",
            "",
            "**Quote:**",
            "",
            *[f"> {line}" for line in (i["quote"] or "").splitlines()],
            "",
            "| Code re-check | Result |",
            "|---|---|",
            f"| Source host is exactly aws.amazon.com (https) | {'yes' if pipeline.is_official_aws_url(i['source_url']) else '**no**'} |",
            f"| Every quoted sentence is word for word in that page's body_text or title | {'yes' if on_page else '**no**'} |",
            "",
            "Checked by hand:",
            "",
            "- [ ] Opened the source link and it is the page named above",
            "- [ ] Found the quote in the page's body_text, word for word",
            "- [ ] The quote backs every fact in the claim",
            "",
            f"[Trace]({i['trace_link']})" if i.get("trace_link") else "",
            "",
        ]
    SPOTCHECK_FILE.write_text("\n".join(lines), encoding="utf-8")


def build_static_page() -> None:
    """docs/index.html: briefing.html with the holdout results built in, for GitHub Pages."""
    data = json.dumps(holdout_status()).replace("</", "<\\/")
    slot = '<script id="briefing-data" type="application/json">null</script>'
    template = PAGE.read_text(encoding="utf-8")
    if slot not in template:
        sys.exit(f"{PAGE.name} has no data slot, so the page could not be built.")
    STATIC_PAGE.parent.mkdir(exist_ok=True)
    STATIC_PAGE.write_text(template.replace(slot, slot.replace("null", data)), encoding="utf-8")
    (STATIC_PAGE.parent / ".nojekyll").touch()  # GitHub Pages: serve the file as is


def holdout_status() -> dict:
    """What the briefing's holdout list should show."""
    csv_name = str(HOLDOUT_FILE.relative_to(ROOT))
    if not HOLDOUT_FILE.exists():
        return {"status": "no_csv", "csv": csv_name}
    if not HOLDOUT_RESULTS.exists():
        return {"status": "not_run", "csv": csv_name}
    data = json.loads(HOLDOUT_RESULTS.read_text(encoding="utf-8"))
    stale = HOLDOUT_FILE.stat().st_mtime > HOLDOUT_RESULTS.stat().st_mtime
    # A holdout claim the checker was built and tuned on doesn't test it on anything new, so flag it.
    built_on = {" ".join(r["claim_text"].split()).lower() for r in pipeline.load_rows()}
    seen = [i["candidate_id"] for i in data["items"] if " ".join(i["claim"].split()).lower() in built_on]
    return {"status": "ready", "csv": csv_name, "stale": stale, "seen_before": seen, **data}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/holdout":
            self.send_json(200, holdout_status())
            return
        if self.path not in ("/", "/briefing.html"):
            self.send_error(404)
            return
        data = PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/check":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            claim = (json.loads(self.rfile.read(length) or b"{}").get("claim") or "").strip()
        except (ValueError, AttributeError):
            self.send_json(400, {"error": "Send JSON like {\"claim\": \"...\"}."})
            return
        if not claim:
            self.send_json(400, {"error": "Type a claim first."})
            return
        if len(claim) > MAX_CLAIM_LENGTH:
            self.send_json(400, {"error": f"Keep the claim under {MAX_CLAIM_LENGTH} characters."})
            return
        try:
            self.send_json(200, check(claim))
        except Exception as error:  # model or network failure: report it instead of hanging the page
            self.send_json(502, {"error": f"The check could not finish: {error}"})

    def log_message(self, format, *args):
        sys.stderr.write(f"{self.address_string()} {format % args}\n")


if __name__ == "__main__":
    if "--holdout" in sys.argv[1:]:
        build_holdout(publish="--publish" in sys.argv[1:])
    else:
        print(f"Claim checker running at http://{HOST}:{PORT}")
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
