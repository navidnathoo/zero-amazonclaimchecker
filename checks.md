# Safety checks

The two checks in `tests/test_safety.py`, run on the lists in `summary.json` from the latest full pipeline run. `pipeline.py` runs the same checks before it builds the briefing and stops if either fails.

| Check | Result |
|---|---|
| 1. Every confirmed item has a `source_url` containing aws.amazon.com and a non-empty quote | Pass |
| 2. Every rejected item has a non-empty reason | Pass |

## Check 1: confirmed items

| Candidate | source_url | Contains aws.amazon.com? | Quote | Quote non-empty? | Result |
|---|---|---|---|---|---|
| C-01 | https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/ | yes | "Amazon Bedrock AgentCore is now generally available / Amazon Bedrock AgentCore is now generally available. AgentCore is an agentic platform to build, deploy and operate AI agents securely at scale, using any framework and any foundation model. AgentCore adds support for VPC, AWS PrivateLink and AWS CloudFormation. Amazon Bedrock AgentCore is available in nine AWS Regions: US East (N. Virginia), US East (Ohio), US West (Oregon), Asia Pacific (Mumbai), Asia Pacific (Singapore), Asia Pacific (Sydney), Asia Pacific (Tokyo), Europe (Frankfurt) and Europe (Ireland)." | yes (564 characters) | Pass |
| C-04 | https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-aurora-dsql-generally-available/ | yes | "Amazon Aurora DSQL is now generally available / Amazon Aurora DSQL is now generally available. / Aurora DSQL is a serverless, distributed SQL database with virtually unlimited scale, active-active high availability, PostgreSQL compatibility and no infrastructure to manage." | yes (269 characters) | Pass |

## Check 2: rejected items

| Candidate | Reason | Reason non-empty? | Result |
|---|---|---|---|
| C-02 | Check 1 failed: no source page on aws.amazon.com in the snapshot matches this claim. | yes (84 characters) | Pass |
| C-03 | Check 3 failed: 'The UltraServers are available in all commercial AWS Regions' is not backed (The sentences say availability is through EC2 Capacity Blocks for ML in the Dallas Local Zone (us-east-1-dfw-2a), an extension of the US East (N. Virginia) Region. They do not say anything about all commercial AWS Regions). | yes (317 characters) | Pass |
| C-05 | Check 3 failed: 'The service is generally available (GA)' is not backed (The sentences say the service is in preview, not GA); 'It works at massive scale' is not backed (The sentences do not mention scale. They mention cost reduction of up to 90%). | yes (248 characters) | Pass |

## Sample failure (on purpose)

This sample shows what a failed safety check looks like. It is **not** a real pipeline result: the two items below were made up and run through the real checks to show how they fail. The real results above all pass.

Sample lists:

```json
{
  "confirmed": [
    {"candidate_id": "C-05", "source_url": "https://www.reddit.com/r/aws/", "quote": "Amazon S3 Vectors is now GA", "trace_link": "sample"}
  ],
  "rejected": [
    {"candidate_id": "C-02", "reason": "", "trace_link": "sample"}
  ]
}
```

| Check | Candidate | Value checked | Result | Why it fails |
|---|---|---|---|---|
| 1. Confirmed item has an aws.amazon.com `source_url` and a non-empty quote | C-05 | https://www.reddit.com/r/aws/ | **Fail** | The source is a Reddit thread, not aws.amazon.com. |
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
Safety check failed, so no briefing was built: C-05: source_url is not on aws.amazon.com
```

The pipeline exits with code 1 and prints no briefing. It stops at the first failure, so it reports C-05 and doesn't reach C-02. pytest runs both checks and reports both.
