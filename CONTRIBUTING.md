# Contributing to ProfitPilot

Welcome! We're thrilled you want to contribute to ProfitPilot. This guide will help you get started quickly.

**👉 New here?** Start with the [README.md](./README.md) to understand the project, then come back here.

---

## 🚀 Development Setup

### Prerequisites
- **Git** (for version control)
- **Docker & Docker Compose** (recommended for full setup)
- **Python 3.10+** (for backend development)
- **Node.js 18+** (for frontend development)
- **PostgreSQL** (included in Docker Compose)

### Clone & Install

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/business-ai-agent.git
cd business-ai-agent

# Copy environment template (create .env if needed)
cp .env.example .env  # or create from environment variables section

# Start services with Docker (recommended)
docker-compose up -d

# OR: Manual setup (see README.md for detailed steps)
# Install Python dependencies
pip install -r requirements.txt

# Install dependencies for each service
cd dashboard && npm install
cd ../landing-page && npm install
cd ../agent_code && pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the root directory with:
```
POSTGRES_USER=admin
POSTGRES_PASSWORD=root
POSTGRES_DB=test_db
LLM_API_KEY=your_key_here
SLACK_BOT_TOKEN=your_token_here
```
See `README.md` for a complete list of variables.

---

## 📂 Project Structure

| Directory | Purpose |
|-----------|---------|
| `agent_code/` | Python backend (LangGraph, Flask, LLM integrations) |
| `dashboard/` | Next.js admin dashboard |
| `landing-page/` | Marketing landing page (Vite + React) |
| `web/` | Flask web service & chatbot UI |
| `whatsapp_gateway/` | WhatsApp integration service |
| `tests/` | Unit tests for backend |

---

## 🎮 Running Locally

### Using Docker (Recommended)
```bash
docker-compose up -d
```
- **Backend API**: http://localhost:5000
- **Dashboard**: http://localhost:3000
- **Landing Page**: http://localhost:5173
- **Database UI (PgAdmin)**: http://localhost:5050

### Without Docker

**Backend (Python)**
```bash
cd agent_code
python app_main.py
```

**Dashboard (Next.js)**
```bash
cd dashboard
npm run dev  # http://localhost:3000
```

**Landing Page (Vite)**
```bash
cd landing-page
npm run dev  # http://localhost:5173
```

---

## 🎨 Code Style & Linting

### Python (Backend)
```bash
# Format code with Ruff
ruff format agent_code/

# Lint with Ruff
ruff check agent_code/

# Fix issues automatically
ruff check --fix agent_code/
```

### TypeScript (Frontend)
```bash
cd dashboard  # or landing-page
npm run lint        # Run ESLint
npm run format      # Run Prettier
```

**Before committing:** Run linting tools to avoid CI failures.

---

## 📝 Commit Message Convention

We follow **Conventional Commits**. Format your messages as:

```
<type>(<scope>): <subject>

<body (optional)>
<footer (optional)>
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring (no feature/fix changes)
- `chore:` — Dependencies, config, tooling
- `test:` — Test additions/updates

**Examples:**
```
feat(agent): Add context memory for multi-turn conversations
fix(dashboard): Resolve chart rendering on mobile
docs(CONTRIBUTING): Add testing section
refactor(parser): Optimize database query execution
```

---

## 🌿 Branch Naming

Use descriptive branch names:
```
feat/add-memory-context
fix/dashboard-mobile-bug
docs/update-setup-guide
refactor/optimize-db-queries
chore/update-dependencies
```

---

## 🔄 PR Process

1. **Fork the repository** on GitHub
2. **Create a new branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Make your changes** and commit with conventional messages
4. **Push to your fork**:
   ```bash
   git push origin feat/your-feature-name
   ```
5. **Open a PR** with a clear description of what you've done
6. **Link the issue** (e.g., "Closes #123")
7. **Respond to review feedback** courteously

### What Makes a Good PR?
- ✅ Solves **one issue** (no mixing unrelated changes)
- ✅ Includes **passing tests**
- ✅ Follows **code style guidelines**
- ✅ Has a **clear description** of changes
- ✅ Includes **documentation** if needed
- ✅ All checks pass (CI/linting)

---

## 🏷️ Claiming Issues

**Important for GSSoC Participants:**

1. **Comment** on the issue: "I'd like to work on this" or similar
2. **Wait for assignment** before starting work
3. **Do not start work without approval** — this prevents duplicate efforts
4. Once assigned, you have **2-3 weeks** to submit a PR (check issue details)
5. If stuck, **ask for help** in comments — we're here to support!

---

## 🧪 Testing

### Python Tests
```bash
cd agent_code
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_auth.py

# Run with coverage
python -m pytest --cov=agent_code tests/
```

### Frontend Tests (if applicable)
```bash
cd dashboard
npm test
```

**Write tests for new features!** Check existing tests for patterns.

---

## 📋 Additional Guidelines

### Code Reviews
- Reviews are **constructive & collaborative**
- Ask questions; don't assume
- Approve once concerns are addressed

### Documentation
- Update **README.md** if adding features
- Add **inline comments** for complex logic
- Update API docs if changing endpoints

### Performance
- Test with real data when possible
- Avoid unnecessary API calls
- Monitor database query performance

### Security
- **Never** commit API keys or secrets
- Use `.env` files for sensitive data
- Validate user inputs on backend

---

## 🤝 Community & Support

- **Stuck?** Open a discussion or comment on the issue
- **Found a bug?** Report it with a reproducible example
- **Have an idea?** Start a discussion before coding

---

**This project follows [GSSoC 2025](https://www.girlscriptsummerofcode.in/) contribution guidelines. Thank you for making ProfitPilot better! 🚀**
