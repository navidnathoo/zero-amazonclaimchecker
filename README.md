# zero-amazonclaimchecker

Checks whether a claimed AWS launch is real, against a snapshot of 40 official aws.amazon.com pages captured on 3 November 2025.

**Briefing page:** [docs/index.html](docs/index.html), to be served at https://navidnathoo.github.io/zero-amazonclaimchecker/

The briefing lists every holdout claim with a Confirmed or Rejected badge, the quote that backs a confirmed claim or the reason a claim was rejected, and a public LangSmith trace for each one. The page carries its own data, so no server is needed to view it.

## Status

| Item | State |
|---|---|
| RIV-HO holdout batch (RIV-HO-01 to RIV-HO-05) | **Not run.** The batch hasn't been provided. `data/aws_reinvent_candidate_items_holdout.csv` is still a copy of the original five claims (C-01 to C-05), and the briefing labels it as not a true holdout set. |
| Refresh snapshot (`data/aws_official_source_snapshot_refresh.json`) | **Not provided.** When it is added, the researcher loads it automatically on top of the 3 November snapshot, and `spotcheck.md` re-checks each confirmed quote against its `body_text`. |
| Spot check by hand | **Not done.** The boxes in `spotcheck.md` are for a reviewer to tick or fail once the RIV-HO run lands. |
| GitHub Pages | **Off.** The link above returns 404 until Pages is set to deploy `main` from `/docs` in the repository settings. |

When the RIV-HO batch and refresh file are in `data/`, one command reruns everything and rebuilds the page:

```bash
.venv/bin/python app.py --holdout --publish 2>&1 | tee holdout_run.log
```

## How a claim is checked

`pipeline.py` runs each claim through a LangGraph graph: **Lead → Researcher → Fact-checker → Lead**, following the rule card in [confirm_rule.md](confirm_rule.md):

1. Is there a source page on aws.amazon.com in the snapshot?
2. Are the quoted sentences copied word for word from that page?
3. Do they back every fact in the claim?

Any no rejects the claim. Checks 1 and 2 are tested in code; the model answers check 3, listing every fact with the exact words that back it.

Before anything is saved or published, the safety checks in [tests/test_safety.py](tests/test_safety.py) must pass: every confirmed item needs an https source whose host is exactly `aws.amazon.com` and a non-empty quote, and every rejected item needs a reason. If either fails, nothing is written.

## Files

| File | What it is |
|---|---|
| [docs/index.html](docs/index.html) | The published briefing (built by `app.py --holdout`) |
| [holdout_run.log](holdout_run.log) | Full output of the run that built it: the safety checks pass before the page is built |
| [spotcheck.md](spotcheck.md) | Every confirmed holdout claim, re-checked against the snapshot, with boxes to confirm by hand |
| [results.md](results.md) | Results for the five candidate claims, with every fact checked |
| [checks.md](checks.md) | The safety check data, plus a sample failure |
| [audit.md](audit.md) | Earlier wrong answers, what caused them and the fix |

## Run it locally

Needs `OPENROUTER_API_KEY` and the LangSmith settings in `.env` (see `.env.example`).

```bash
.venv/bin/python app.py                        # live checker at http://127.0.0.1:8765
.venv/bin/python app.py --holdout --publish    # check the holdout CSV, then rebuild the briefing
.venv/bin/python pipeline.py                   # check the five candidate claims
.venv/bin/python -m pytest tests/test_safety.py
```

The OpenRouter model is set by `OPENROUTER_MODEL` (currently `anthropic/claude-haiku-5.5`).
