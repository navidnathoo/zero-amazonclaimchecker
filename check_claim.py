"""Ask the model whether one candidate claim is a real AWS launch, traced in LangSmith."""

import csv
import sys
from pathlib import Path

from langsmith import traceable
from langsmith.wrappers import wrap_openai

from openrouter_client import DEFAULT_MODEL, get_client

DATA_FILE = Path(__file__).parent / "data" / "aws_reinvent_candidate_items.csv"
RULE_FILE = Path(__file__).parent / "confirm_rule.md"
QUESTION = "Is this a real AWS launch? Answer yes or no, and name the page that proves it."


def load_row(candidate_id: str) -> dict:
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["candidate_id"] == candidate_id:
                return row
    sys.exit(f"No row with candidate_id {candidate_id} in {DATA_FILE}")


@traceable(name="check_claim")
def check_claim(row: dict) -> str:
    client = wrap_openai(get_client())
    rule = RULE_FILE.read_text(encoding="utf-8")
    prompt = f"Claim: {row['claim_text']}\n\n{QUESTION}"
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": rule},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    candidate_id = sys.argv[1] if len(sys.argv) > 1 else "C-02"
    row = load_row(candidate_id)
    print(f"{candidate_id}: {row['claim_text']}\n")
    print(check_claim(row, langsmith_extra={"metadata": {"candidate_id": candidate_id}}))
