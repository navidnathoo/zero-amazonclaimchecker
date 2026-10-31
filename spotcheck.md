# Spot check: confirmed holdout claims

Holdout run of 2026-10-31 08:26 UTC. Each confirmed claim below was re-checked by code against `data/aws_official_source_snapshot.json`. Open each source and tick the boxes to confirm it by hand.

## C-01

**Claim:** Amazon Bedrock AgentCore is now generally available for building and running AI agents at scale.

**Source:** [Amazon Bedrock AgentCore is now generally available](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/) (published 2025-10-13)

**Quote:**

> Amazon Bedrock AgentCore is now generally available. AgentCore is an agentic platform to build, deploy and operate AI agents securely at scale, using any framework and any foundation model. AgentCore adds support for VPC, AWS PrivateLink and AWS CloudFormation. Amazon Bedrock AgentCore is available in nine AWS Regions: US East (N. Virginia), US East (Ohio), US West (Oregon), Asia Pacific (Mumbai), Asia Pacific (Singapore), Asia Pacific (Sydney), Asia Pacific (Tokyo), Europe (Frankfurt) and Europe (Ireland).

| Code re-check | Result |
|---|---|
| Source host is exactly aws.amazon.com (https) | yes |
| Every quoted sentence is word for word on the snapshot page | yes |

Checked by hand:

- [ ] Opened the source link and it is the page named above
- [ ] Found the quote on the live page, word for word
- [ ] The quote backs every fact in the claim

[Trace](https://smith.langchain.com/public/feacae3b-0a98-410e-84ea-57e8f8e10843/r)

## C-04

**Claim:** Amazon Aurora DSQL is now generally available as a serverless distributed SQL database with active-active high availability.

**Source:** [Amazon Aurora DSQL is now generally available](https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-aurora-dsql-generally-available/) (published 2025-05-27)

**Quote:**

> Amazon Aurora DSQL is now generally available.
> Aurora DSQL is a serverless, distributed SQL database with virtually unlimited scale, active-active high availability, PostgreSQL compatibility and no infrastructure to manage.

| Code re-check | Result |
|---|---|
| Source host is exactly aws.amazon.com (https) | yes |
| Every quoted sentence is word for word on the snapshot page | yes |

Checked by hand:

- [ ] Opened the source link and it is the page named above
- [ ] Found the quote on the live page, word for word
- [ ] The quote backs every fact in the claim

[Trace](https://smith.langchain.com/public/01bb1282-f61e-4590-9d50-8de4dc765a69/r)
