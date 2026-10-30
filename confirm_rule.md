# Confirm rule

Use this rule every time a claim is checked. Answer each question yes or no, in order.

1. **Source page:** Is there a source page for the claim on aws.amazon.com?
2. **Exact quote:** Is there a quote copied word for word from that page?
3. **Full support:** Does that quote back every fact in the claim, such as the service, what launched, the Region and the date?

A claim is confirmed only if all three answers are yes. Any no rejects the claim, with a one-line reason that names the check that failed.

## Answer format

```
Check 1 (source page on aws.amazon.com): yes/no, <URL or "none">
Check 2 (exact quote from that page): yes/no, "<quote>" or "none"
Check 3 (quote backs every fact): yes/no
Verdict: CONFIRMED | REJECTED: <one-line reason>
```
