"""Local server for briefing.html: check one claim, and list the holdout claims' results.

    .venv/bin/python app.py              # then open http://127.0.0.1:8765
    .venv/bin/python app.py --holdout    # check every claim in the holdout CSV and save the results

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


def build_holdout() -> None:
    """Checks every claim in the holdout CSV. Saves the results only if the safety checks pass."""
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
    results = []
    for row in rows:
        print(f"Checking {row['candidate_id']}: {row['claim_text']}")
        results.append(pipeline.run(row))
    wait_for_all_tracers()
    pipeline.add_trace_links(results)

    failure = pipeline.safety_checks(pipeline.lead_summary(results))
    if failure:
        sys.exit(f"Safety check failed: {failure}\nNothing was saved to {HOLDOUT_RESULTS.name}.")

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
            "quote": without_title(r["quote"], page) if confirmed else None,
            "reason": None if confirmed else pipeline.full_reason(r),
            "trace_link": r.get("trace_link"),
        })
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    HOLDOUT_RESULTS.write_text(json.dumps({"run_at": run_at, "model": pipeline.DEFAULT_MODEL, "items": items},
                                          indent=2) + "\n", encoding="utf-8")
    print(f"Safety checks passed. Saved {len(items)} results to {HOLDOUT_RESULTS.relative_to(ROOT)}.")


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
        build_holdout()
    else:
        print(f"Claim checker running at http://{HOST}:{PORT}")
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
