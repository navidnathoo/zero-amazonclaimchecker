# Rule card: AWS launch claim check

Candidate claims such as "Amazon S3 Vectors is now GA" are collected from blogs, newsletters and forums. Before a claim is treated as a real AWS launch, a checker compares it with the official AWS source snapshot (`data/aws_official_source_snapshot.json`), which holds pages from aws.amazon.com.

## The rule: a claim is confirmed only if every answer is yes

1. Is there a source page for this claim on aws.amazon.com in the snapshot?
2. Is there a quote copied word for word from that page?
3. Does that quote back every fact in the claim, such as the service, what launched (GA or preview), the Regions and the date?

If any answer is no, the claim is rejected, with one line saying which check failed. If the checker is unsure, the answer is no.

## Who does what

| Agent | Gets | Gives back |
|---|---|---|
| Organizer | The claim | The matching snapshot page and an exact quote from it, or "no match" |
| Checker | The claim, the page and the quote | Confirmed or rejected, with a one-line reason |

## Worked example

Claim (C-03): "Amazon EC2 P6e-GB200 UltraServers accelerated by NVIDIA Grace Blackwell are now available in all commercial AWS Regions."

Page the organizer found: https://aws.amazon.com/about-aws/whats-new/2025/07/amazon-ec2-p6e-gb200-ultraservers-available/

Quote: "P6e-GB200 UltraServers are available through EC2 Capacity Blocks for ML in the Dallas Local Zone (us-east-1-dfw-2a), an extension of the US East (N. Virginia) Region."

| Check | Answer |
|---|---|
| 1. Source page on aws.amazon.com | Yes |
| 2. Exact quote from that page | Yes |
| 3. Quote backs every fact | No. The page says the Dallas Local Zone only; the claim says all commercial Regions. |

Verdict: rejected. Reason: "Region mismatch: the page says the Dallas Local Zone only, the claim says all commercial Regions."
