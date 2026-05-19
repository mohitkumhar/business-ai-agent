# Security Policy

Thank you for helping keep ProfitPilot safe. Please report suspected
vulnerabilities responsibly so maintainers have time to investigate and fix
them before details are public.

## Supported Versions

Security fixes target the default branch and the latest published release. The
project is under active development, so older branches and forks may not receive
separate fixes.

## Reporting a Vulnerability

Do not open a public issue or pull request that includes exploit details,
tokens, private data, or a working attack path.

Preferred reporting path:

1. Use GitHub private vulnerability reporting if it is enabled for the
   repository.
2. If private vulnerability reporting is not available, contact the maintainer
   listed in `README.md` through GitHub and share only the minimum information
   needed to establish a private channel.
3. If you need a public tracker, open a minimal issue titled `security: <short
   summary>` without exploit details.

Helpful details to include privately:

- Affected component, such as the Flask agent, dashboard, landing page,
  WhatsApp gateway, Docker setup, or CI workflow.
- Impact and realistic attack scenario.
- Steps to reproduce in a local or test environment.
- Relevant logs, screenshots, or proof-of-concept notes with secrets removed.
- Suggested fix, if you already have one.

## Response Expectations

Maintainers aim to acknowledge valid reports within 7 days and provide an
initial triage update within 14 days. Timelines may vary for complex reports or
volunteer availability.

## Out of Scope

General bugs, dependency update requests, and configuration questions should be
opened through the normal issue templates unless they create a clear security
risk.
