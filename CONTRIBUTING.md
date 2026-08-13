# Contributing

1. Create a branch from `main`.
2. Install the development dependencies: `python -m pip install -e '.[dev]'`.
3. Run `pytest`, `python -m compileall mybusiness_mcp`, and `ruff check mybusiness_mcp tests`.
4. Keep API behavior driven by Google Discovery Documents. A legacy endpoint may
   use a narrow, version-controlled bundled catalog only when Google no longer
   publishes a working Discovery Document, the endpoint remains officially
   documented, and contract tests cover its methods and schemas.
5. Follow `SECURITY.md` and never commit OAuth client secrets, authorization
   codes, access/refresh tokens, ADC files, private keys, signed URLs, or
   location/customer data.

## Secret check before pushing

If Gitleaks is installed locally, scan the complete repository history before
pushing security-sensitive changes:

```bash
gitleaks git --redact --verbose .
```

The GitHub `Secret Scan` workflow repeats this check on pushes and pull
requests. A real secret must be revoked or rotated; deleting it in a later
commit is not sufficient because the original value remains in Git history.

Use obvious placeholders in documentation and tests. Do not weaken the scanner
with broad allowlists to make CI pass. If a finding is a true false positive,
add the narrowest rule-specific exception that explains why it is safe.

## Commit identity privacy

Git author names and email addresses are stored in commit history. If you do
not want to publish a personal email address, configure Git to use the
GitHub-provided `noreply` address shown in your GitHub email settings before
creating commits.
