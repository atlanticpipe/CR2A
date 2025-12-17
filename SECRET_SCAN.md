# Secret Scan Report

- **Date:** 2025-12-17T12:11:34Z
- **Scope:** Entire repository (/workspace/CR2A).
- **Method:** Manual regex sweeps with ripgrep for common credential formats: OpenAI sk-..., AWS AKIA..., GitHub ghp_..., Google AIza....

## Results
- No live secrets detected in the scanned patterns.
- AWS-style matches are confined to vendored example or data files under cr2a-lambda-build/ (e.g., boto3/examples/cloudfront.rst, botocore/data/.../examples-1.json) and contain documented placeholders such as AKIAIOSFODNN7EXAMPLE only.

## Commands Executed
- rg "sk-[A-Za-z0-9]{32,}" .
- rg "AKIA[0-9A-Z]{16}" .
- rg "ghp_[A-Za-z0-9]{36}" .
- rg "AIza[0-9A-Za-z\-_]{35}" .

No further action required.
