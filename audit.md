# Audit: facts, quotes and verdicts

This audit checks every fact in the five candidate claims against the quote the pipeline copied from the AWS source snapshot (`data/aws_official_source_snapshot.json`). It lists the facts that were not supported directly by a quote, the fact results that were not 100% accurate, and every wrong verdict or reason, with its fix.

## Summary

- **No final verdict was wrong.** C-01 and C-04 are confirmed; C-02, C-03 and C-05 are rejected, in every version of the pipeline that used the snapshot.
- **One fact result was wrong.** C-03's "accelerated by NVIDIA Grace Blackwell" was marked not backed, but the AWS page's own title states it. This is now fixed.
- **Three reasons were wrong or incomplete** in earlier versions. Each was fixed (see "Wrong responses and fixes").

## 1. Facts not supported directly by a quote

Results from the run before the fix.

| Claim | Fact | Result | Correct? |
|---|---|---|---|
| C-02 | Every fact (managed quantum computing Region in us-east-1 at re:Invent 2025) | No page in the snapshot | Yes. No AWS page announces it. |
| C-03 | "accelerated by NVIDIA Grace Blackwell" | Not backed | **No.** The body says "NVIDIA GB200 NVL72", but the page title says "accelerated by NVIDIA Grace Blackwell GPUs". |
| C-03 | "in all commercial AWS Regions" | Not backed | Yes. The page says the Dallas Local Zone (us-east-1-dfw-2a) only. |
| C-05 | "now GA" | Not backed | Yes. The page says "now available in preview". |
| C-05 | "at massive scale" | Not backed | Yes. The page gives limits ("up to 10,000 vector indexes" per bucket) but never says "massive scale". |

### Backed by meaning, not by the same words

These facts are backed, but the quote uses different words. They are judgment calls, so the fact table in `results.md` now marks them "yes (same meaning)".

| Claim | Fact | Words in the quote |
|---|---|---|
| C-01 | "building and running AI agents" | "build, deploy and operate AI agents" ("operate" for "running") |
| C-05 | "store and query vector embeddings" | "store and query vectors" ("vectors" for "vector embeddings") |
| C-05 | "natively in S3" | "S3 Vectors is the first cloud object store with native support to store and query vectors" |

## 2. Fact results that were not 100% accurate

| Claim | Problem | Effect |
|---|---|---|
| C-03 | "Grace Blackwell" marked not backed, though the page title states it. | The rejection reason named two gaps where there is only one. The verdict was still right, because the Regions fact fails. |
| C-05 | "natively in S3" changed between runs: backed in two runs, not backed in one. | The fact-checker is a model, and close calls can flip between runs. The verdict didn't change, because the GA fact fails every time. |
| C-05 | In the latest run, GA was listed twice, as two facts with different wording. | Cosmetic: the same gap is reported twice. |

## 3. Wrong responses and fixes

| # | Claim | Response before | Why it was wrong | Fix |
|---|---|---|---|---|
| 1 | C-03 | Rejected at check 2: "the sentences are not copied exactly from the source page." | Both sentences were exact. The researcher skipped the sentence between them, so the joined text didn't appear as one unbroken stretch on the page. | Check 2 now tests each copied sentence on its own. |
| 2 | C-03, C-05 | C-03 rejected only for Regions; C-05 only for GA. | Incomplete. C-05 also claims "massive scale", which the quote doesn't back. The fact-checker stopped at the first gap. | The fact-checker now lists every fact with the exact words that back it, and code rejects any evidence that isn't in the quote. |
| 3 | C-03 | Rejected with two gaps: "'The UltraServers are accelerated by NVIDIA Grace Blackwell' is not backed (…never use the words 'Grace Blackwell')" and "all commercial AWS Regions". | The Grace Blackwell gap was false. The researcher could only quote the page body, and the fact was in the page title. | The page title is now always copied as the first sentence, and check 2 accepts the title as part of the page. |

### Fix 3, before and after (C-03)

| Fact | Before | After |
|---|---|---|
| Service is Amazon EC2 P6e-GB200 UltraServers | yes | yes |
| Accelerated by NVIDIA Grace Blackwell | **no** | yes: "accelerated by NVIDIA Grace Blackwell GPUs" (page title) |
| Now available | yes | yes |
| Available in all commercial AWS Regions | no | no: the page says the Dallas Local Zone only |

**Verdict:** rejected both times. After the fix, the reason names only the real gap: "Check 3 failed: 'Available in all commercial AWS Regions' is not backed."

**New trace (public):** https://smith.langchain.com/public/f3a77a70-d610-494c-a3af-0aa6b1136832/r

## Limits that remain

- The fact-checker is a model. Close calls such as "natively in S3" can change from run to run. Code checks that the evidence is copied exactly, but not that the model judged its meaning correctly.
- Vague claim words such as "massive scale" can never be backed by an exact quote, so a claim that uses them is always rejected, even if the service really is large.
- The snapshot was captured on 3 November 2025. Launches after that date can't be confirmed.
