<div align="center">

<img src="https://img.shields.io/badge/GirlScript%20Summer%20of%20Code-2025-orange?style=for-the-badge&logo=girlscript&logoColor=white" alt="GSSoC 2025"/>
<img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge" alt="Active"/>
<img src="https://img.shields.io/badge/PRs-Welcome-blueviolet?style=for-the-badge" alt="PRs Welcome"/>
<img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License"/>

# 🤖 ProfitPilot — AI Business Helper Chatbot

**An intelligent AI-powered business advisor that helps small business owners make smarter decisions using their own data.**

[📋 Problem Statement](./PS.md) · [🚀 Quick Start](#-quick-start-docker) · [🗺️ Architecture](#️-architecture) · [🤝 Contributing](#-contributing-gssoc-guide) · [📬 Contact](#-contact)

</div>

---

## 📌 Table of Contents

- [What Is This Project?](#-what-is-this-project)
- [Tech Stack](#-tech-stack)
- [Architecture](#️-architecture)
- [Services & Ports](#-services--ports)
- [Quick Start (Docker)](#-quick-start-docker)
- [Manual Setup (Without Docker)](#-manual-setup-without-docker)
- [Database Setup](#-database-setup)
- [Environment Variables](#-environment-variables)
- [Contributing — GSSoC Guide](#-contributing-gssoc-guide)
- [Good First Issues](#-good-first-issues)
- [Project Structure](#-project-structure)
- [Known Issues](#-known-issues--open-for-contribution)
- [Contact](#-contact)

---

## 💡 What Is This Project?

Small business owners take important decisions every day — ads spending, hiring, pricing — often without clear data. **ProfitPilot** is an AI business partner that:

- 🧠 **Understands your business data** (sales, expenses, employees, products)
- 💬 **Answers natural-language questions** via a streaming AI chatbot
- ⚠️ **Warns about risky decisions** before they're made
- 📊 **Shows a real-time business health score**
- 📈 **Provides a monitoring dashboard** with Grafana, Prometheus & Loki

> _"This is not just a chatbot. It is an AI business partner that thinks before the owner acts."_

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI / LLM** | [LangGraph](https://langchain-ai.github.io/langgraph/) + [Ollama](https://ollama.com) (`llama3.2:3b`) |
| **Backend Agent** | Python 3.11 · Flask · SSE Streaming |
| **Database** | PostgreSQL 16 · SQLite (chat history) |
| **Dashboard** | Next.js 14 (TypeScript) |
| **Landing Page** | Vite · TanStack Start · TanStack Router |
| **Monitoring** | Prometheus · Grafana · Loki · Promtail |
| **DevOps** | Docker · Docker Compose |

---

## 🗺️ Architecture

```
Browser
  ├── Landing Page (Vite / TanStack :5173)
  │       POST /api/v1/onboarding ──────► Flask Agent (:5000) ──► PostgreSQL (:5432)
  │       Google OAuth (client-side)
  │
  ├── Dashboard (Next.js :3001)
  │       /api/* ── rewrite ──► AGENT_API_URL (Flask Agent)
  │       Charts, KPIs, Employee Stats, Alerts
  │
  ├── Flask Agent (:5000) — LangGraph Intent Router
  │       ├── General Information (Web Search via DuckDuckGo)
  │       ├── Database Request (SQL generation + execution)
  │       ├── Logs Request    (LogQL → Loki)
  │       └── Metrics Request (PromQL → Prometheus)
  │
  └── Observability Stack
        Prometheus (:9090) ← scrapes Flask + Next.js
        Promtail ──► Loki (:3100)
        Grafana (:3000) ← reads Loki + Prometheus
```

### Chat / Query Flow

```
User types question
      ↓
Intent Detection (Ollama LLM)
      ↓
┌─────────────────────────────────┐
│  general  │  database  │  logs  │  metrics  │
└─────────────────────────────────┘
      ↓
LangGraph Subgraph executes
      ↓
SSE streaming response to browser
```

---

## 📡 Services & Ports

| Service | URL | Description |
|---------|-----|-------------|
| 🌐 **Landing Page** | http://localhost:5173 | Onboarding & marketing site |
| 🤖 **Flask Agent API** | http://localhost:5000 | AI chatbot backend |
| 📊 **Dashboard** | http://localhost:3001 | Business analytics dashboard |
| 🗄️ **pgAdmin** | http://localhost:5050 | PostgreSQL UI (`admin@admin.com` / `root`) |
| 📈 **Grafana** | http://localhost:3000 | Monitoring dashboards |
| 🔥 **Prometheus** | http://localhost:9090 | Metrics server |
| 🪵 **Loki** | http://localhost:3100 | Log aggregation |
| 🐘 **PostgreSQL** | localhost:5432 | Main database |

---

## 🚀 Quick Start (Docker)

> **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Step 1 — Clone the repository

```bash
git clone https://github.com/mohitkumhar/business-ai-agent.git
cd business-ai-agent
```

### Step 2 — Create the environment file

Create a `.env` file in the **root** directory:

```bash
# .env (root)
DATABASE_URL=postgresql://admin:root@db:5432/test_db
```

Create a `.env` file inside `agent_code/`:

```bash
# agent_code/.env
DATABASE_URL=postgresql://admin:root@postgres_db:5432/test_db
LLM_BASE_URL=http://host.docker.internal:11434/
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
```

> **Note:** Ollama must be running on your **host machine** (not inside Docker). Download it from [ollama.com](https://ollama.com) and run:
> ```bash
> ollama pull llama3.2:3b
> ollama serve
> ```

### Step 3 — Start all services

```bash
docker compose up --build
```

This will start PostgreSQL, the Flask agent, Next.js dashboard, landing page, and the full observability stack.

### Step 4 — Set up the database

Once the containers are running, apply the database schema and seed data:

```bash
# Copy SQL files into the running Postgres container
docker cp company_db_schema.sql <postgres-container-name>:/company_db_schema.sql
docker cp inserts.sql <postgres-container-name>:/inserts.sql

# Get the container name
docker ps

# Access the container
docker exec -it <postgres-container-name> bash

# Inside the container, run:
psql -U admin -d test_db -f /company_db_schema.sql
psql -U admin -d test_db -f /inserts.sql
exit
```

### Step 5 — Access the app

| Service | URL |
|---------|-----|
| Landing Page | http://localhost:5173 |
| Dashboard | http://localhost:3001 |
| Agent API | http://localhost:5000 |

### Stop all services

```bash
docker compose down
```

---

## 🔧 Manual Setup (Without Docker)

Use this if you want to run individual services for development.

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- [Ollama](https://ollama.com) with `llama3.2:3b` model

### 1. Flask Agent Backend

```bash
cd agent_code

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Create agent_code/.env with:
# DATABASE_URL=postgresql://admin:root@localhost:5432/test_db
# LLM_BASE_URL=http://127.0.0.1:11434/
# GROQ_API_KEY=your_groq_api_key_here

# Run
python app.py
# Agent runs on http://localhost:5000
```

### Running Backend Tests

The Flask backend includes pytest coverage that runs without a real database by
mocking database calls and external integrations.

```bash
cd agent_code
pip install -r requirements.txt pytest
pytest tests -v
```

The GitHub Actions CI workflow also runs `pytest agent_code/tests -v` whenever
the `agent_code/tests/` directory is present.

### 2. Next.js Dashboard

```bash
cd dashboard
npm install

# Set environment variable
export AGENT_API_URL=http://localhost:5000   # Linux/Mac
set AGENT_API_URL=http://localhost:5000      # Windows

npm run dev
# Dashboard runs on http://localhost:3000
```

### 3. Landing Page

```bash
cd landing-page
npm install
npm run dev
# Landing page runs on http://localhost:5173
```

### 4. Legacy Web Flask (Optional)

```bash
cd web
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5001 — full SQL dashboard APIs
```

---

## 🗄️ Database Setup

> Skip this if you already ran the Docker quick start steps.

### Docker Compose credentials

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` |
| User | `admin` |
| Password | `root` |
| Database | `test_db` |

### pgAdmin Access

- URL: http://localhost:5050
- Email: `mohitmolela@gmail.com`
- Password: `root`

### Apply Schema & Seed Data

```bash
# 1. Find your postgres container name
docker ps

# 2. Copy files into the container
docker cp company_db_schema.sql <container>:/company_db_schema.sql
docker cp inserts.sql <container>:/inserts.sql

# 3. Enter the container
docker exec -it <container> bash

# 4. Apply schema (creates all tables)
psql -U admin -d test_db -f /company_db_schema.sql

# 5. Insert seed data
psql -U admin -d test_db -f /inserts.sql

# 6. Verify
psql -U admin -d test_db -c "\dt"
```

---

## 🔐 Environment Variables

| Variable | Service | Description | Default |
|----------|---------|-------------|---------|
| `DATABASE_URL` | Agent, Web | PostgreSQL connection string | `postgresql://admin:root@localhost:5432/test_db` |
| `GROQ_API_KEY` | Agent | Groq API key for `ChatOpenAI` calls that use the Groq OpenAI-compatible endpoint | — |
| `GEMINI_API_KEY` | Agent | Gemini Vision API key for OCR-based image transaction extraction | — |
| `OPENROUTER_API_KEY` | Agent | OpenRouter API key for LangGraph subgraph LLM calls | — |
| `OPENROUTER_MODEL` | Agent | OpenRouter model used by the base LLM client | `openai/gpt-4o-mini` |
| `PROMETHEUS_URL` | Agent | Prometheus API URL | `http://prometheus:9090` |
| `LOKI_URL` | Agent | Loki API URL | `http://loki:3100` |
| `AGENT_API_URL` | Dashboard, Web | Flask agent base URL | `http://localhost:5000` |
| `NEXT_PUBLIC_AGENT_API_URL` | Dashboard | Browser-visible Flask agent URL for direct client requests | `http://localhost:5000` |
| `NEXT_PUBLIC_LANDING_URL` | Dashboard | Public landing page URL used by dashboard links | `http://localhost:5173` |
| `NEXT_PUBLIC_SLACK_APP_URL` | Dashboard | Optional Slack app install or launch URL | — |
| `RATE_LIMIT_DEFAULT` | Agent | Default Flask-Limiter quota for API clients | `200 per day;50 per hour` |
| `RATE_LIMIT_AUTH` | Agent | Signup/login quota per client IP | `5 per minute` |
| `RATE_LIMIT_CHAT` | Agent | Chat generation quota per client IP | `10 per minute` |
| `RATE_LIMIT_IMPORT` | Agent | Transaction import quota per client IP | `20 per hour` |
| `TELEGRAM_BOT_TOKEN` | Agent | Telegram BotFather token used by `/api/v1/telegram/webhook` to send AI replies | - |
| `VITE_API_URL` | Landing Page | Flask agent URL used by onboarding requests | `http://localhost:5000` |
| `VITE_GOOGLE_CLIENT_ID` | Landing Page | Google OAuth Client ID | — |
| `NEXTAUTH_URL` | Landing Page | Local auth callback base URL | `http://localhost:5173` |
| `NEXT_PUBLIC_VIEWER_URL` | Landing Page | Public viewer URL for the landing app | `http://localhost:5173` |
| `ENCRYPTION_SECRET` | Landing Page | Local encryption secret for app integrations | — |
| `MY_WHATSAPP_NUMBER` | WhatsApp Gateway | E.164 WhatsApp number without `+` | — |
| `WHATSAPP_VERIFY_TOKEN` | Agent | Meta webhook verification token | — |
| `WHATSAPP_ACCESS_TOKEN` | Agent | Meta WhatsApp API access token | — |
| `WHATSAPP_PHONE_NUMBER_ID` | Agent | Meta WhatsApp phone number ID | — |
| `JWT_SECRET` | Agent | High-entropy JWT signing secret for Flask auth tokens; required and must not use the sample value | — |
| `CHAT_DB_PATH` | Agent | SQLite file path for chat history persistence | `chat_history.db` |
| `DEFAULT_BUSINESS_ID` | Agent | Fallback business ID for integrations without a session | — |
| `GITHUB_REPO` | Agent | Repository used by GitHub issue helper flows | `mohitkumhar/intelligent-business-agent` |
| `API_KEY` | Agent auth | Simple API key | `secret-token` |

Copy `.env.example` to `.env`, fill private values locally, generate `JWT_SECRET` with a high-entropy value such as `openssl rand -hex 32`, and never commit real `.env` files:

```bash
cp .env.example .env
```

---

### Dashboard authentication flow

All `/api/dashboard/*` endpoints are protected and identify the caller **only** from a JWT — never from a client-supplied `email` query parameter:

1. The user logs in via `POST /api/auth/login`, which returns a signed JWT (HS256, signed with `JWT_SECRET`) carrying the `user_id` and `business_id`.
2. The dashboard stores the token (`localStorage` key `profit_pilot_token`).
3. Every dashboard request sends `Authorization: Bearer <token>`; the backend's `@token_required` decorator decodes it and derives the tenant's `business_id` server-side.
4. Each query is scoped with `WHERE business_id = %s` so a token for one business can never read another's data.

There is no anonymous/email fallback — requests without a valid token receive `401`.

---

### Telegram Webhook

Set `TELEGRAM_BOT_TOKEN`, then configure your Telegram bot webhook to POST updates to:

```text
https://<your-agent-domain>/api/v1/telegram/webhook
```

Text messages and captions are forwarded to the AI agent. Photo, document, or voice updates without captions receive a helpful fallback message instead of failing silently.

---

## 🤝 Contributing — GSSoC Guide

Welcome to GirlScript Summer of Code 2025! 🎉 We're excited to have you. Follow these steps to make your first contribution.

---

### 📋 Step 1 — Find an Issue

1. Go to the [Issues tab](https://github.com/mohitkumhar/business-ai-agent/issues)
2. Look for issues labeled:
   - `good first issue` — perfect for beginners
   - `gssoc` — GSSoC-tagged issues
   - `bug` — known bugs to fix
   - `enhancement` — new features to build
3. Read the issue description fully before picking it

> 💡 **Never start working without being assigned first!** Comment on the issue: _"I'd like to work on this."_

---

### 🍴 Step 2 — Fork & Clone

```bash
# Fork the repo on GitHub (click the Fork button)

# Then clone YOUR fork
git clone https://github.com/<your-username>/business-ai-agent.git
cd business-ai-agent

# Add the original repo as upstream
git remote add upstream https://github.com/mohitkumhar/business-ai-agent.git

# Verify
git remote -v
```

---

### 🌿 Step 3 — Create a Branch

```bash
# Always sync with upstream first
git fetch upstream
git checkout main
git merge upstream/main

# Create your feature branch
git checkout -b fix/your-issue-description
# Examples:
# git checkout -b fix/import-requests-loki
# git checkout -b feat/add-env-example
# git checkout -b docs/improve-readme
```

> **Branch naming convention:**
> - `fix/` — bug fixes
> - `feat/` — new features
> - `docs/` — documentation changes
> - `refactor/` — code refactoring

---

### 💻 Step 4 — Make Your Changes

- Keep changes **focused** on the issue you're solving
- Follow the existing code style
- Add comments where the logic isn't obvious
- Test your changes locally before pushing

---

### ✅ Step 5 — Commit & Push

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "fix: add missing import requests in loki utils"
# or
git commit -m "feat: add .env.example file"

# Push to your fork
git push origin fix/your-issue-description
```

**Commit message format:**
```
<type>: <short description>

Examples:
fix: resolve table name mismatch business vs businesses
feat: add .env.example with all required variables
docs: update README with correct Flask port number
refactor: extract SSE handler into separate module
```

---

### 🔁 Step 6 — Open a Pull Request

1. Go to **your fork** on GitHub
2. Click **"Compare & pull request"**
3. Fill in the PR template:
   - What issue does this fix? (e.g., `Closes #42`)
   - What changes did you make?
   - How did you test it?
4. Request a review and wait for feedback

> ⏰ Maintainers will review PRs within a few days. Be patient and responsive to feedback!

---

### ✍️ PR Checklist

Before submitting, make sure:

- [ ] The code runs without errors locally
- [ ] I have tested the specific feature/fix I changed
- [ ] My branch is up-to-date with `upstream/main`
- [ ] I have written a clear commit message
- [ ] I have linked the issue in the PR description (`Closes #<issue-number>`)
- [ ] I have not introduced unrelated changes

---

## 🌟 Good First Issues

Here are great starting points for first-time contributors:

| # | Task | Difficulty | Files to Edit |
|---|------|-----------|---------------|
| 1 | Add `.env.example` with all required variables | ⭐ Easy | Create new file |
| 2 | Add a backend health-check endpoint test | ⭐ Easy | `agent_code/tests/` |
| 3 | Fix `about.tsx` Typebot branding → ProfitPilot | ⭐ Easy | `landing-page/src/routes/_layout/about.tsx` |
| 4 | Add missing `import requests` in Loki utils | ⭐⭐ Medium | `agent_code/intents/logs_request_graph/utils.py` |
| 5 | Add missing `import time` in Metrics utils | ⭐⭐ Medium | `agent_code/intents/metrics_request_graph/utils.py` |
| 6 | Fix `AVAILABLE_TABLES` table name `business` → `businesses` | ⭐⭐ Medium | `agent_code/intents/database_request_graph/subgraph.py` |
| 7 | Fix Next.js chatbot to handle SSE streaming | ⭐⭐⭐ Hard | `dashboard/src/app/chatbot/page.tsx` |
| 8 | Add `web/` Flask service to `docker-compose.yml` | ⭐⭐ Medium | `docker-compose.yml` |
| 9 | Document landing-page API URL overrides for non-Docker deployments | ⭐ Easy | `README.md` |
| 10 | Add unit tests for intent detection | ⭐⭐⭐ Hard | Create `agent_code/tests/` |

---

## 📁 Project Structure

```
business-ai-agent/
│
├── agent_code/              # 🤖 Flask + LangGraph AI Backend (Port 5000)
│   ├── app.py               # Main Flask app — API routes, SSE streaming
│   ├── app_main.py          # Alternative entry point
│   ├── db_config.py         # PostgreSQL connection helpers
│   ├── ocr_processor.py     # OCR utility for document parsing
│   ├── query_execution.py   # SQL query execution engine
│   ├── seed_db.py           # Database seeding script
│   ├── transaction_import.py
│   ├── intents/             # LangGraph subgraphs per intent
│   │   ├── database_request_graph/    # SQL generation + execution
│   │   ├── general_information_graph/ # Web search (DuckDuckGo)
│   │   ├── logs_request_graph/        # LogQL → Loki
│   │   └── metrics_request_graph/     # PromQL → Prometheus
│   ├── nodes/               # LangGraph node handlers
│   ├── llm/                 # Ollama LLM abstraction
│   ├── logger/              # Rotating file logger
│   ├── state/               # LangGraph state types
│   ├── slack_integration/   # Slack bot integration
│   └── utils/               # Shared utilities
│
├── dashboard/               # 📊 Next.js Analytics Dashboard (Port 3001)
│   ├── src/app/             # App Router pages
│   │   ├── page.tsx         # Main dashboard with KPIs & charts
│   │   ├── chatbot/         # Chat interface (SSE issue — open for fix!)
│   │   └── api/             # API route handlers
│   ├── src/components/      # Chart and card components
│   ├── src/lib/api.ts       # Centralized API calls + mock fallback
│   └── next.config.ts       # API rewrites to Flask agent
│
├── landing-page/            # 🌐 Marketing + Onboarding (Port 5173)
│   ├── src/routes/          # TanStack Router pages
│   │   ├── index.tsx        # Home page
│   │   ├── get-started.tsx  # Onboarding form
│   │   └── login.tsx        # Authentication
│   └── src/components/      # UI components
│
├── web/                     # 🗄️ Legacy Flask Dashboard (Port 5001)
│   ├── app.py               # Full SQL-backed dashboard APIs
│   └── templates/           # Jinja HTML templates
│
├── whatsapp_gateway/        # 📱 WhatsApp integration
├── company_db_schema.sql    # PostgreSQL schema (DDL)
├── inserts.sql              # Seed data (demo business)
├── docker-compose.yml       # All services orchestration
├── prometheus.yml           # Prometheus scrape config
├── promtail-config.yaml     # Log shipping to Loki
└── requirements.txt         # Root Python dependencies
```

---

## 🐛 Known Issues — Open for Contribution

These are confirmed bugs. Each is a great contribution opportunity!

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | `get-started.tsx` hardcodes `localhost:5000` (breaks in prod) | 🔴 High | `landing-page/src/routes/get-started.tsx` |
| 2 | Next.js chatbot uses `res.json()` on SSE stream — won't work | 🔴 Critical | `dashboard/src/app/chatbot/page.tsx` |
| 3 | `logs_request_graph/utils.py` missing `import requests` | 🔴 High | `agent_code/intents/logs_request_graph/utils.py` |
| 4 | `metrics_request_graph/utils.py` missing `import time` | 🔴 High | `agent_code/intents/metrics_request_graph/utils.py` |
| 5 | `AVAILABLE_TABLES` uses `business` instead of `businesses` | 🔴 High | `agent_code/intents/database_request_graph/subgraph.py` |
| 6 | `web/` Flask not in `docker-compose.yml` | 🟡 Medium | `docker-compose.yml` |
| 7 | Landing page API URL needs deployment-specific override docs | 🟡 Medium | `README.md` |
| 8 | `about.tsx` still shows Typebot branding | 🟢 Low | `landing-page/src/routes/_layout/about.tsx` |
| 9 | Add an `.env.example` file for local setup | 🟢 Low | Root directory |
| 10 | No `.env.example` file in repo | 🟡 Medium | Root directory |

---

## 🗣️ Getting Help

Stuck? Here's how to get help:

1. **Check existing issues** — your question might already be answered
2. **Open a new issue** — describe your problem clearly with error messages
3. **Join the GSSoC Discord** — connect with other contributors
4. **Tag maintainers** in your issue if it's urgent

> 💬 Don't be shy to ask questions — everyone starts somewhere!

---

## 📜 Code of Conduct

This project follows the [GirlScript Code of Conduct](https://github.com/GirlScriptSummerOfCode). Be respectful, inclusive, and kind. Harassment of any kind will not be tolerated.

---

## 📬 Contact

| Maintainer | GitHub |
|-----------|--------|
| Mohit Kumar | [@mohitkumhar](https://github.com/mohitkumhar) |

---

## ⭐ Support the Project

If you find this project useful or interesting:

- ⭐ **Star** this repository
- 🍴 **Fork** it to contribute
- 📢 **Share** it with others in the GSSoC community

---

<div align="center">

Made with ❤️ for **GirlScript Summer of Code 2025**

<img src="https://img.shields.io/github/stars/mohitkumhar/business-ai-agent?style=social" alt="Stars"/>
<img src="https://img.shields.io/github/forks/mohitkumhar/business-ai-agent?style=social" alt="Forks"/>

</div>
