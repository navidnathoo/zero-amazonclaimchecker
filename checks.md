# Safety checks

The two checks in `tests/test_safety.py`, run on the lists in `summary.json` from the pipeline run of 2026-10-31 06:55 UTC. `results.md` and this file come from the same run.

`pipeline.py` runs these checks after it builds the lists and before it writes anything. If either check fails, it doesn't write `results.md` or `summary.json`, builds no briefing, and exits with an error.

A source counts as on aws.amazon.com only if it is an https URL whose host is exactly `aws.amazon.com`. Containing the text is not enough.

| Check | Result |
|---|---|
| 1. Every confirmed item has a `source_url` on aws.amazon.com and a non-empty quote | Pass |
| 2. Every rejected item has a non-empty reason | Pass |

## Check 1: confirmed items

| Candidate | source_url | Host is aws.amazon.com? | Quote | Quote non-empty? | Result |
|---|---|---|---|---|---|
| C-01 | https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/ | yes | "Amazon Bedrock AgentCore is now generally available / Amazon Bedrock AgentCore is now generally available. / AgentCore is an agentic platform to build, deploy and operate AI agents securely at scale, using any framework and any foundation model." | yes (241 characters) | Pass |
| C-04 | https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-aurora-dsql-generally-available/ | yes | "Amazon Aurora DSQL is now generally available / Amazon Aurora DSQL is now generally available. / Aurora DSQL is a serverless, distributed SQL database with virtually unlimited scale, active-active high availability, PostgreSQL compatibility and no infrastructure to manage. / Single-Region clusters offer 99.99% availability and multi-Region clusters offer 99.999% availability." | yes (372 characters) | Pass |

## Check 2: rejected items

| Candidate | Reason | Reason non-empty? | Result |
|---|---|---|---|
| C-02 | Check 1 failed: no source page on aws.amazon.com in the snapshot matches this claim. | yes (84 characters) | Pass |
| C-03 | Check 3 failed: 'Available in all commercial AWS Regions' is not backed (The sentences only say the UltraServers are available through EC2 Capacity Blocks for ML in the Dallas Local Zone (us-east-1-dfw-2a), an extension of the US East (N. Virginia) Region. They do not say availability extends to all commercial Regions). | yes (321 characters) | Pass |
| C-05 | Check 3 failed: 'The service is generally available (GA)' is not backed (The sentences say 'now available in preview' and 'The preview is available in...', not GA); 'It works at massive scale' is not backed (The sentences only say it can reduce the cost of uploading, storing and querying vectors by up to 90%. They make no scale claim). | yes (337 characters) | Pass |

## Sample failure (on purpose)

This sample shows what a failed safety check looks like. It is **not** a real pipeline result: the two items below were made up and run through the real checks to show how they fail. The real results above all pass.

Sample lists:

```json
{
  "confirmed": [
    {"candidate_id": "C-05", "source_url": "https://aws.amazon.com.example.net/s3-vectors-ga", "quote": "Amazon S3 Vectors is now GA", "trace_link": "sample"}
  ],
  "rejected": [
    {"candidate_id": "C-02", "reason": "", "trace_link": "sample"}
  ]
}
```

| Check | Candidate | Value checked | Result | Why it fails |
|---|---|---|---|---|
| 1. Confirmed item has a `source_url` on aws.amazon.com and a non-empty quote | C-05 | https://aws.amazon.com.example.net/s3-vectors-ga | **Fail** | The host is aws.amazon.com.example.net, not aws.amazon.com. The URL contains the text, so the old substring check would have let it through. |
| 2. Rejected item has a non-empty reason | C-02 | `""` (empty) | **Fail** | The reason is blank, so nobody can tell why the claim was rejected. |

### What pytest shows

```
tests/test_safety.py::test_confirmed_items_have_aws_source_and_quote FAILED
tests/test_safety.py::test_rejected_items_have_reason FAILED
E   AssertionError: C-05: source_url is not on aws.amazon.com
E   AssertionError: C-02: reason is empty
2 failed
```

### What pipeline.py shows

```
Safety check failed: C-05: source_url is not on aws.amazon.com
Nothing was written to results.md or summary.json and no briefing was built. The blocked lists are in summary.blocked.json.
```

The pipeline exits with code 1. `results.md` and `summary.json` keep the last run that passed. It stops at the first failure, so it reports C-05 and doesn't reach C-02. pytest runs both checks and reports both.
