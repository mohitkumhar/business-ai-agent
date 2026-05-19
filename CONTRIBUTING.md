# Contributing to ProfitPilot

Thanks for helping improve ProfitPilot. This project welcomes bug fixes,
documentation, tests, UI work, integrations, and small reliability
improvements that make the AI business agent easier to run and maintain.

## Before You Start

1. Check the existing issues and pull requests to avoid duplicate work.
2. Comment on the issue you want to work on and wait for maintainer guidance
   when the issue is marked for GSSoC or has an assignee.
3. Keep changes focused. A pull request should solve one problem clearly.
4. Do not commit secrets, generated local logs, virtual environments, or
   dependency folders.
5. For suspected security issues, follow `SECURITY.md` instead of opening a
   public issue with exploit details.

## Local Setup

Clone the repository and install the Python dependencies:

```powershell
git clone https://github.com/mohitkumhar/business-ai-agent.git
cd business-ai-agent
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r agent_code\requirements.txt
```

Install frontend dependencies only for the app you are changing:

```powershell
cd dashboard
npm install

cd ..\landing-page
npm install

cd ..\whatsapp_gateway
npm install
```

To run the full Docker stack:

```powershell
docker compose up --build
```

## Development Checks

Run the checks relevant to your change before opening a pull request:

```powershell
pytest
```

```powershell
cd dashboard
npm run lint
npm run build
```

```powershell
cd landing-page
npm run check-types
npm run build
```

If a check cannot be run locally, mention the reason in your pull request.

## Pull Request Guidelines

1. Create your work on a new branch.
2. Keep commits readable and scoped to the change.
3. Fill in the pull request template.
4. Link the related issue using `Closes #<issue-number>` when applicable.
5. Include screenshots or short recordings for visible UI changes.
6. Add or update tests when changing behavior.
7. Update documentation when setup, configuration, or user-facing behavior
   changes.

## Commit Message Style

Use short, descriptive commit messages. Conventional prefixes are welcome:

- `fix:` for bug fixes
- `feat:` for new behavior
- `docs:` for documentation-only changes
- `test:` for test changes
- `chore:` for maintenance

## Review Expectations

Maintainers may ask for smaller diffs, clearer tests, or documentation updates.
Please respond constructively and keep the discussion tied to the code.
