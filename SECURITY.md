# Security Policy

## Supported code

Security fixes apply to the latest `main` branch. Older commits and abandoned branches are not maintained as supported releases.

## Reporting a vulnerability

Prefer GitHub Private Vulnerability Reporting from the repository's **Security** tab when it is available.

Do not place live credentials, OAuth codes, access tokens, refresh tokens, private keys, signed URLs, customer data, Business Profile account IDs, or location data in a public issue, pull request, discussion, screenshot, or log.

If private vulnerability reporting is unavailable, open a minimal public issue containing no sensitive value and ask the maintainer to establish a private reporting channel.

## Secret-handling requirements

The repository must not contain real:

- Google OAuth client JSON files or `client_secret` values;
- Application Default Credentials (ADC) files;
- OAuth authorization codes, access tokens, or refresh tokens;
- Google Cloud service-account keys or other private keys;
- API keys, passwords, signed URLs, or credential-bearing connection strings;
- Google Business Profile customer, account, location, review, or operational data copied from production.

Authentication must remain external to the repository. For local use, keep credential files outside the checkout and reference them through Application Default Credentials or environment variables.

Documentation and tests may use placeholders only. Placeholder values must be obviously non-live, for example `YOUR_OAUTH_CLIENT_JSON`, `PATH_TO_APPLICATION_DEFAULT_CREDENTIALS_JSON`, or `<redacted>`.

## Automated controls

This repository uses two layers of secret detection:

1. GitHub Secret Scanning / Push Protection at the repository platform layer.
2. Gitleaks in GitHub Actions, scanning the complete Git history with the repository's `.gitleaks.toml` policy.

The secret-scan check must not be bypassed for a real credential. False positives should be narrowed with the smallest possible rule-specific allowlist; do not add broad path exclusions for source, tests, documentation, or configuration files.

GitHub Actions workflows should use least-privilege `GITHUB_TOKEN` permissions, disable persisted checkout credentials when a workflow does not push, and pin third-party actions to immutable commit SHAs.

## If a secret is exposed

Treat any credential committed to Git as compromised, even if a later commit deletes it.

1. Revoke or rotate the credential at the issuing provider first.
2. Remove the sensitive value from the current tree and Git history where practical.
3. Remove stale branches or tags that still reference the exposed commit.
4. Review GitHub secret-scanning alerts and workflow logs for additional copies.
5. Re-run the secret scan across the full history before considering the incident closed.

History rewriting does not make a previously exposed credential trustworthy again; rotation or revocation is still required.

## Contributor privacy

Git commit author names and email addresses are part of repository history. Contributors who do not want to publish a personal email should configure Git to use the GitHub-provided `noreply` address shown in their GitHub email settings before committing.
