# Maintainers

This file lists the maintainers responsible for reviewing pull requests,
triaging issues, and guiding contributors.

## Current Maintainers

| Name | GitHub | Areas |
| --- | --- | --- |
| Mohit Kumar | [@mohitkumhar](https://github.com/mohitkumhar) | Overall project, backend agent, dashboard, integrations, CI |

## Ownership Areas

| Area | Paths |
| --- | --- |
| Backend agent | `agent_code/`, `requirements.txt`, `tests/` |
| Dashboard | `dashboard/` |
| Landing page | `landing-page/` |
| Legacy Flask web app | `web/` |
| Integrations | `whatsapp_gateway/`, `TELEGRAM_INTEGRATION_GUIDE.md`, `WHATSAPP_INTEGRATION_GUIDE.md` |
| Infrastructure and CI | `.github/`, `docker-compose.yml`, `prometheus.yml`, `promtail-config.yaml` |
| Documentation | `README.md`, `CONTRIBUTING.md`, `SUPPORT.md`, project guides |

## Review Expectations

- Pull requests should stay focused and link the related issue when possible.
- Maintainers should prefer clear, actionable review comments.
- Large changes may be split into smaller pull requests before review.
- Security reports should follow `SECURITY.md` and avoid public exploit details.
