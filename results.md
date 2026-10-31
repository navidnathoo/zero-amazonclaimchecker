# Results

Each claim was checked by `pipeline.py` (Lead, Researcher, Fact-checker) against `data/aws_official_source_snapshot.json` using `anthropic/claude-haiku-5.5`, following `confirm_rule.md`.

| Candidate | Claim | Verdict | Source URL and quote | Reason | Trace |
|---|---|---|---|---|---|
| C-01 | Amazon Bedrock AgentCore is now generally available for building and running AI agents at scale. | confirmed | https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/<br>"Amazon Bedrock AgentCore is now generally available Amazon Bedrock AgentCore is now generally available. AgentCore is an agentic platform to build, deploy and operate AI agents securely at scale, using any framework and any foundation model." | All three checks passed. | [trace](https://smith.langchain.com/public/5dd91f91-6826-4928-9f87-b2461a599d1f/r) |
| C-02 | AWS will launch a managed quantum computing Region in us-east-1 at re:Invent 2025. | rejected | no match | Check 1 failed: no source page on aws.amazon.com in the snapshot matches this claim. | [trace](https://smith.langchain.com/public/23250ea9-7a5d-456c-98bd-689a0671c172/r) |
| C-03 | Amazon EC2 P6e-GB200 UltraServers accelerated by NVIDIA Grace Blackwell are now available in all commercial AWS Regions. | rejected | https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-ec2-p6e-gb200-ultraservers-available/<br>"Amazon EC2 P6e-GB200 UltraServers accelerated by NVIDIA Grace Blackwell GPUs are now available Amazon EC2 P6e-GB200 UltraServers, accelerated by NVIDIA GB200 NVL72, are now available. P6e-GB200 UltraServers are available through EC2 Capacity Blocks for ML in the Dallas Local Zone (us-east-1-dfw-2a), an extension of the US East (N. Virginia) Region." | Check 3 failed: 'Available in all commercial AWS Regions' is not backed (The sentences name only one location: the Dallas Local Zone (us-east-1-dfw-2a), described as an extension of the US East (N. Virginia) Region. They say nothing about all commercial AWS Regions). | [trace](https://smith.langchain.com/public/f3a77a70-d610-494c-a3af-0aa6b1136832/r) |
| C-04 | Amazon Aurora DSQL is now generally available as a serverless distributed SQL database with active-active high availability. | confirmed | https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-aurora-dsql-generally-available/<br>"Amazon Aurora DSQL is now generally available Amazon Aurora DSQL is now generally available. Aurora DSQL is a serverless, distributed SQL database with virtually unlimited scale, active-active high availability, PostgreSQL compatibility and no infrastructure to manage." | All three checks passed. | [trace](https://smith.langchain.com/public/c0f7d4ec-db75-4d5d-ac80-51d4537cf4dc/r) |
| C-05 | Amazon S3 Vectors is now GA and lets you store and query vector embeddings natively in S3 at massive scale. | rejected | https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-s3-vectors-preview-native-support-storing-querying-vectors/<br>"Amazon S3 Vectors (Preview): native support for storing and querying vectors Amazon S3 Vectors is now available in preview. S3 Vectors is the first cloud object store with native support to store and query vectors, and can reduce the cost of uploading, storing and querying vectors by up to 90%. Each vector bucket holds up to 10,000 vector indexes. S3 Vectors integrates with Amazon Bedrock Knowledge Bases and Amazon OpenSearch Service. The preview is available in the US East (N. Virginia), US East (Ohio), US West (Oregon), Europe (Frankfurt) and Asia Pacific (Sydney) Regions." | Check 3 failed: 'The service is now GA (generally available)' is not backed (The copied sentences say the service is in preview, not GA; the heading also says 'Amazon S3 Vectors (Preview)'); 'It is available at massive scale' is not backed (The sentences say each vector bucket holds up to 10,000 vector indexes and cut costs by up to 90%; they do not describe 'massive scale' or the service being at scale); 'Launch stage is GA (the claim implies generally available, not preview)' is not backed (The sentences state the launch stage is preview). | [trace](https://smith.langchain.com/public/5b50a6a8-63e8-4c50-afde-976bdd21a51c/r) |

## Every fact, checked against the quote

### C-01

| Fact in the claim | Backed? | Words from the quote, or what it says instead |
|---|---|---|
| The service is Amazon Bedrock AgentCore | yes | "Amazon Bedrock AgentCore is now generally available" |
| The launch stage is generally available (GA) | yes | "Amazon Bedrock AgentCore is now generally available." |
| It is for building and running AI agents | yes (same meaning) | "build, deploy and operate AI agents securely at scale" |
| It works at scale | yes | "at scale" |

### C-02

No facts checked: the claim failed before check 3.

### C-03

| Fact in the claim | Backed? | Words from the quote, or what it says instead |
|---|---|---|
| Service is Amazon EC2 P6e-GB200 UltraServers | yes | "Amazon EC2 P6e-GB200 UltraServers accelerated by NVIDIA Grace Blackwell GPUs are now available" |
| Accelerated by NVIDIA Grace Blackwell | yes | "accelerated by NVIDIA Grace Blackwell GPUs" |
| Launch status is now available | yes | "are now available" |
| Available in all commercial AWS Regions | **no** | The sentences name only one location: the Dallas Local Zone (us-east-1-dfw-2a), described as an extension of the US East (N. Virginia) Region. They say nothing about all commercial AWS Regions. |

### C-04

| Fact in the claim | Backed? | Words from the quote, or what it says instead |
|---|---|---|
| The service is Amazon Aurora DSQL | yes | "Amazon Aurora DSQL is now generally available." |
| The launch stage is generally available (GA) | yes | "Amazon Aurora DSQL is now generally available" |
| It is a serverless database | yes | "Aurora DSQL is a serverless, distributed SQL database" |
| It is a distributed SQL database | yes | "Aurora DSQL is a serverless, distributed SQL database" |
| It provides active-active high availability | yes | "active-active high availability" |

### C-05

| Fact in the claim | Backed? | Words from the quote, or what it says instead |
|---|---|---|
| The service is Amazon S3 Vectors | yes | "Amazon S3 Vectors is now available in preview." |
| The service is now GA (generally available) | **no** | The copied sentences say the service is in preview, not GA; the heading also says 'Amazon S3 Vectors (Preview)'. |
| It lets you store and query vector embeddings natively in S3 | yes (same meaning) | "S3 Vectors is the first cloud object store with native support to store and query vectors" |
| It is available at massive scale | **no** | The sentences say each vector bucket holds up to 10,000 vector indexes and cut costs by up to 90%; they do not describe 'massive scale' or the service being at scale. |
| Launch stage is GA (the claim implies generally available, not preview) | **no** | The sentences state the launch stage is preview. |
