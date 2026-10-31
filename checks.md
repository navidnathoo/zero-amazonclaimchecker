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
