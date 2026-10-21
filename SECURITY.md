# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.
Email the maintainer listed on the repository profile, or use GitHub's private
vulnerability reporting if enabled.

## What not to put in issues or PRs

- API keys, tokens, cookies, or session dumps
- Broker / exchange credentials
- Real account statements, live P&L, or production ledgers
- Scraped social posts that include private DMs or non-public content
- Personal contact details of third parties

If you paste a secret by mistake, rotate it immediately and open a private report.

## Scope of this project

`agent-market-ops` ships **demo / synthetic** data only. It is not a trading
system and must not be connected to live order routers without your own
security review.
