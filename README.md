# zero-amazonclaimchecker

Checks whether a claimed AWS launch is real. `check_claim.py` reads a row from `data/aws_reinvent_candidate_items.csv`, asks the model through OpenRouter *"Is this a real AWS launch? Answer yes or no, and name the page that proves it."*, prints the answer, and records the call in LangSmith.

```bash
.venv/bin/python check_claim.py C-02
```

## Result for C-02

**Claim:** AWS will launch a managed quantum computing Region in us-east-1 at re:Invent 2025.

**Model's answer:**

> **No.** I'm not aware of any AWS announcement of a managed quantum computing Region in us-east-1 at re:Invent 2025, so I can't name a page that proves it. I also can't check live sources, so I can't rule out a late announcement. The claim may be mixing up existing services. Amazon Braket is AWS's managed quantum computing service and is available in us-east-1, but it's a service, not a separate Region. To verify the claim, check AWS's "What's New" feed (aws.amazon.com/about-aws/whats-new) and the re:Invent 2025 session catalog.

**LangSmith trace:** https://smith.langchain.com/public/21f13ce4-dd97-4b7f-b675-6075f9035c7a/r/3de151e7-b03f-4690-b148-ab4827e44091?start_time=2026-10-30T11%3A59%3A51.230376Z

The model didn't name an official AWS page that proves the claim, and the claim's only source is the Hacker News (Y Combinator) front page.

The Openrouter Model we're using is: anthropic/claude-haiku-5.5
