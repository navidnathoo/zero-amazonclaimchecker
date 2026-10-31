# Rule card: AWS launch claim check

Candidate claims are collected from blogs, newsletters and forums. Before a claim is treated as a real AWS launch, it is checked against the official AWS source snapshot (`data/aws_official_source_snapshot.json`, pages from aws.amazon.com captured 3 November 2025).

## The rule: a claim is confirmed only if every answer is yes

1. Is there a source page for this claim on aws.amazon.com in the snapshot?
2. Are there sentences copied word for word from that page?
3. Do those sentences back every fact in the claim, such as the service, the launch stage (GA or preview), the Regions and the date?

Any no rejects the claim, with a one-line reason saying which check failed. If the answer is unclear, it is no.

## Who does what

| Agent | Job |
|---|---|
| Lead agent | Takes the claim, sends it to the researcher and fact-checker, and writes the final verdict. |
| Researcher | Finds the claim's page on aws.amazon.com in the snapshot and copies the exact sentences that bear on it, or reports no match. |
| Fact-checker | Answers the three checks yes or no, listing every fact in the claim with the exact words that back it, and gives a one-line reason for any no. |

## Worked example 1: C-01 (confirmed)

**Claim:** "Amazon Bedrock AgentCore is now generally available for building and running AI agents at scale."

**Source URL:** https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/

**Sentences copied from the snapshot:**
> Amazon Bedrock AgentCore is now generally available. AgentCore is an agentic platform to build, deploy and operate AI agents securely at scale, using any framework and any foundation model.

| Check | Answer |
|---|---|
| 1. Source page on aws.amazon.com | Yes. The What's New page above, published 13 October 2025. |
| 2. Sentences copied word for word | Yes. Both sentences appear exactly as shown on that page. |
| 3. Sentences back every fact | Yes. Service: Amazon Bedrock AgentCore. Stage: "now generally available". Use: "build, deploy and operate AI agents securely at scale" covers building and running agents at scale. |

**Verdict:** confirmed.

## Worked example 2: C-05 (rejected)

**Claim:** "Amazon S3 Vectors is now GA and lets you store and query vector embeddings natively in S3 at massive scale." (Source: r/aws community thread.)

**Source URL:** https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-s3-vectors-preview-native-support-storing-querying-vectors/

**Sentences copied from the snapshot:**
> Amazon S3 Vectors is now available in preview. S3 Vectors is the first cloud object store with native support to store and query vectors, and can reduce the cost of uploading, storing and querying vectors by up to 90%.

The S3 Vectors product page in the snapshot (https://aws.amazon.com/s3/features/vectors/) says the same: "Amazon S3 Vectors is in preview and is available in five AWS Regions."

| Check | Answer |
|---|---|
| 1. Source page on aws.amazon.com | Yes. The What's New page above, published 15 July 2025. |
| 2. Sentences copied word for word | Yes. Both sentences appear exactly as shown on that page. |
| 3. Sentences back every fact | No. Native store and query: backed. GA: not backed, because both AWS pages say "preview". |

**Verdict:** rejected. Reason: "Check 3 failed: the claim says GA, but both AWS pages say S3 Vectors is in preview."

The rule catches C-05 at check 3. The page is real and the quote is exact, so checks 1 and 2 pass. The Reddit thread got the service right and only the launch stage wrong, and a single wrong fact is enough to reject the claim.
