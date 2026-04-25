# Security Policy

## Supported use

This repository is designed to handle:

- authenticated multi-user API access
- project/run ownership boundaries
- persisted artifacts and traceability metadata
- deployable local or self-hosted environments

Security issues that affect any of those surfaces should be treated seriously.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for a suspected security vulnerability.

Instead, report it privately to the maintainer with:

- a concise description of the issue
- the affected surface
- reproduction steps
- impact assessment
- suggested mitigation if you have one

If you already have an established private contact path with the maintainer, use that. If not, open a minimal public issue asking for a private reporting channel without disclosing details.

## Good reports include

- whether the issue affects auth, data isolation, artifact access, secrets, or deployment posture
- whether it depends on default local-dev configuration
- whether it affects production-safe settings only, dev settings only, or both
- exact versions or commit SHA if known

## Security priorities for this repo

The highest-priority classes are:

- cross-project or cross-user data access
- JWT/session weaknesses
- unsafe default configuration in deployed environments
- artifact content disclosure
- background worker or queue behavior that can corrupt or leak run state
- prompt/report/trace surfaces exposing secrets or private tenant data

## Notes on local development

Some defaults in this repo are intentionally friendlier for local development than for production. That is acceptable only when the boundary is explicit and documented.

A valid security fix in this repo often means:

- keeping development convenience possible
- while making production defaults safe and obvious
