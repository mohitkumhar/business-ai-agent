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
| 🗄️ **pgAdmin** | http://localhost:5050 | PostgreSQL UI (set local credentials in `.env`) |
| 📈 **Grafana** | http://localhost:3000 | Monitoring dashboards |
| 🔥 **Prometheus** | http://localhost:9090 | Metrics server |
| 🪵 **Loki** | http://localhost:3100 | Log aggregation |
| 🐘 **PostgreSQL** | localhost:5432 | Main database, bound to localhost by Compose |

---

## 🚀 Quick Start (Docker)

> **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Step 1 — Clone the repository

```bash
git clone https://github.com/mohitkumhar/business-ai-agent.git
cd business-ai-agent
```

### Step 2 — Create the environment file

Simply copy the `.env.example` template to create your `.env` file in the project's **root** directory:

```bash
cp .env.example .env
```

Open the newly created `.env` file in the root directory and ensure the database credentials and required LLM keys (such as `GROQ_API_KEY`) are set.

Generate local-only database and pgAdmin secrets before starting Compose:

```bash
POSTGRES_PASSWORD_VALUE="$(openssl rand -hex 24)"
PGADMIN_PASSWORD_VALUE="$(openssl rand -hex 24)"

perl -0pi -e "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD_VALUE}|" .env
perl -0pi -e "s|DATABASE_URL=.*|DATABASE_URL=postgresql://profitpilot_dev:${POSTGRES_PASSWORD_VALUE}\@db:5432/test_db|" .env
perl -0pi -e "s|PGADMIN_DEFAULT_EMAIL=.*|PGADMIN_DEFAULT_EMAIL=you\@example.com|" .env
perl -0pi -e "s|PGADMIN_DEFAULT_PASSWORD=.*|PGADMIN_DEFAULT_PASSWORD=${PGADMIN_PASSWORD_VALUE}|" .env
```

Docker Compose runs a preflight check and will stop if placeholder values such as `root`, `admin@admin.com`, or `replace-with-*` are still present.

> [!NOTE]
> For **Docker Compose**, the containerized backend automatically loads variables from this root `.env` file. You do **not** need to create separate `.env` files in service subdirectories.
>
> Ollama must be running on your **host machine** (not inside Docker). Download it from [ollama.com](https://ollama.com) and run:
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

Once the containers are running, apply the Alembic migrations from the repository root and optionally load seed data:

```bash
export DATABASE_URL=postgresql://profitpilot_dev:<your-postgres-password>@localhost:5432/test_db
alembic upgrade head

# Optional demo data
docker cp inserts.sql <postgres-container-name>:/inserts.sql

# Get the container name
docker ps

# Access the container
docker exec -it <postgres-container-name> bash

# Inside the container, run:
psql -U profitpilot_dev -d test_db -f /inserts.sql
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
# DATABASE_URL=postgresql://profitpilot_dev:<your-postgres-password>@localhost:5432/test_db
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
| User | value of `POSTGRES_USER` in `.env` |
| Password | generated value of `POSTGRES_PASSWORD` in `.env` |
| Database | `test_db` |

Compose publishes PostgreSQL and pgAdmin on `127.0.0.1` only by default. If you intentionally need a different host port, set `POSTGRES_HOST_PORT` or `PGADMIN_HOST_PORT` in `.env`; do not bind these services to a public interface for development.

### pgAdmin Access

- URL: http://localhost:5050
- Email: value of `PGADMIN_DEFAULT_EMAIL` in `.env`
- Password: generated value of `PGADMIN_DEFAULT_PASSWORD` in `.env`

### Apply Schema & Seed Data

```bash
# 1. Apply schema migrations from the repository root
export DATABASE_URL=postgresql://profitpilot_dev:<your-postgres-password>@localhost:5432/test_db
alembic upgrade head

# 2. Optional: load demo seed data
docker cp inserts.sql <container>:/inserts.sql
docker exec -it <container> bash
psql -U profitpilot_dev -d test_db -f /inserts.sql

# 3. Verify
psql -U profitpilot_dev -d test_db -c "\dt"
```

### Database Migrations

Alembic is the source of truth for PostgreSQL schema changes going forward. Migration files live in `alembic/`, while `agent_code/db_metadata.py` mirrors the current schema so `--autogenerate` has metadata to compare against.

```bash
# Apply all pending migrations
export DATABASE_URL=postgresql://profitpilot_dev:<your-postgres-password>@localhost:5432/test_db
alembic upgrade head

# Create an autogenerated migration after updating agent_code/db_metadata.py
scripts/create_migration.sh "add customer billing fields"

# Create a manual migration when SQLAlchemy metadata cannot express the change
ALEMBIC_REVISION_MODE=manual scripts/create_migration.sh "add custom index"

# Roll back the latest migration
alembic downgrade -1
```

Seed data remains in `inserts.sql`; migrations should only track schema changes unless a future data migration is explicitly required.

---

## 🔐 Environment Variables

Configuring environment variables correctly is vital for getting **ProfitPilot** up and running. The codebase is organized as a multi-service platform (Vite Landing Page, Next.js Dashboard, Flask Agent Backend), supporting both **Docker Compose** and **Local (manual)** execution.

For security, the backend requires a custom `JWT_SECRET` and will reject the default sample value. Before starting the services, generate a secure key using:
```bash
openssl rand -hex 32
```
Set this as your `JWT_SECRET` in your `.env` file. Never commit real `.env` files to version control.

---

### 📂 File Creation & Placement

The repository includes a single, master `.env.example` in the root directory. Duplicate this template and place it in the correct location depending on your development workflow:

#### Option A: Docker Compose Setup (Recommended)
You only need a single `.env` file in the project's **root** directory:
```bash
# In the root directory:
cp .env.example .env
```
Docker Compose automatically reads this root `.env` file and passes the variables to all services (`backend`, `db`, `dashboard`, etc.).

#### Option B: Local Setup (Manual Running)
For manual local execution, services run in separate processes and load `.env` configurations from their respective folders. Duplicate the root template to:
* **Backend (`agent_code/`)**: `cp .env.example agent_code/.env`
* **Dashboard (`dashboard/`)**: `cp .env.example dashboard/.env`
* **Landing Page (`landing-page/`)**: `cp .env.example landing-page/.env`

---

### 🔄 Docker vs. Local Configuration Differences

Certain variables (such as connection URLs and endpoints) use different hostnames based on whether they run inside Docker containers or on your local machine:

| Variable | Docker Compose Value | Local Setup Value | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://...@{**db**}:5432/...` | `postgresql://...@{**localhost**}:5432/...` | PostgreSQL connection host. Inside Docker, `db` refers to the container service name. |
| `LLM_BASE_URL` | `http://host.docker.internal:11434/` | `http://127.0.0.1:11434/` | Local Ollama endpoint. `host.docker.internal` allows Docker containers to access your host machine. |
| `AGENT_API_URL` | `http://backend:5000` | `http://localhost:5000` | Address used by server processes to communicate with the Flask agent. |
| `PROMETHEUS_URL` | `http://prometheus:9090` | `http://localhost:9090` | Prometheus server scraping endpoint. |
| `LOKI_URL` | `http://loki:3100` | `http://localhost:3100` | Loki log shipper endpoint. |

---

### 🏷️ Environment Variable Categories

The tables below group all supported variables into specific functional domains.

#### 1. Backend Core & Security (Flask Backend)
Defines authentication keys, database settings, and rate-limiting options.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Required** | PostgreSQL connection string. | `postgresql://profitpilot_dev:<generated-password>@db:5432/test_db` |
| `JWT_SECRET` | **Required** | High-entropy JWT signing secret for Flask auth tokens; must not use the sample value. | `replace-with-a-high-entropy-jwt-secret` |
| `API_KEY` | **Required** | Simple static API key used for internal authentication checks. | `secret-token` |
| `CHAT_DB_PATH` | Optional | Path to the SQLite database storing local user chat history. | `chat_history.db` |
| `RATE_LIMIT_DEFAULT` | Optional | Default Flask-Limiter limit for general API clients. | `200 per day;50 per hour` |
| `RATE_LIMIT_AUTH` | Optional | Max signup/login attempts per client IP. | `5 per minute` |
| `RATE_LIMIT_CHAT` | Optional | Max chat requests per client IP. | `10 per minute` |
| `RATE_LIMIT_IMPORT` | Optional | Max file import attempts per client IP. | `20 per hour` |

#### 2. LLM & AI Providers
Required to route queries, execute SQL database tools, and parse documents.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | **Required** | API key used for LangGraph intent routing and SQL generation models via Groq. | `gsk_your_key_here` |
| `GEMINI_API_KEY` | Optional | API key for Gemini Vision models, used for OCR transaction extraction. | `AIzaSy...` |
| `LLM_BASE_URL` | Optional | Ollama model server URL if running local open-source models. | `http://host.docker.internal:11434/` |
| `OPENROUTER_API_KEY`| Optional | API key for routing requests through OpenRouter endpoints. | `sk-or-v1-...` |
| `OPENROUTER_MODEL`  | Optional | Default model selected when using the OpenRouter client. | `openai/gpt-4o-mini` |

#### 3. Frontend Applications (Next.js Dashboard & Vite Landing Page)
Variables prefixed with `NEXT_PUBLIC_` are exposed to client-side browser scripts in Next.js. `VITE_` variables are transpiled for the Vite Landing Page.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `AGENT_API_URL` | **Required** | Server-side URL of the Flask agent backend. | `http://localhost:5000` |
| `NEXT_PUBLIC_AGENT_API_URL` | Optional | Browser-accessible URL of the Flask agent (overrides Next.js proxying). | `http://localhost:5000` |
| `NEXT_PUBLIC_LANDING_URL` | **Required** | Public web URL pointing to the Vite landing/onboarding page. | `http://localhost:5173` |
| `NEXT_PUBLIC_VIEWER_URL`  | **Required** | Public web URL pointing to the viewer interface. | `http://localhost:5173` |
| `VITE_API_URL` | **Required** | Onboarding API URL referenced by the Vite landing page. | `http://localhost:5000` |
| `NEXTAUTH_URL` | Optional | Callback root address for OAuth and credential sessions. | `http://localhost:5173` |
| `VITE_GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID for user login/signup integrations. | `your-google-client-id` |
| `ENCRYPTION_SECRET` | Optional | 32-character encryption key for frontend integration credentials. | `12345678901234567890123456789012` |

#### 4. Observability & Monitoring
Powers the developer performance graphs and container log shipping.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `PROMETHEUS_URL` | Optional | API address where metric scrapes are sent. | `http://prometheus:9090` |
| `LOKI_URL` | Optional | API address of the Loki collector shipping application logs. | `http://loki:3100` |
| `AGENT_MAX_STEPS` | Optional | Safety cap on the maximum steps the AI agent can execute in a single graph run. | `22` |

#### 5. Integrations & Third-Party Channels
Optional configurations to connect your chatbot with external messengers.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Optional | Token from @BotFather to enable messaging via Telegram. | `123456789:ABCdefGh...` |
| `TELEGRAM_WEBHOOK_SECRET` | Required for Telegram webhook | High-entropy secret passed to Telegram's `setWebhook` `secret_token`; incoming webhooks must send it in `X-Telegram-Bot-Api-Secret-Token`. | `replace-with-a-high-entropy-telegram-webhook-secret` |
| `MY_WHATSAPP_NUMBER` | Optional | E.164 phone number without leading `+` to receive WhatsApp alerts. | `911234567890` |
| `WHATSAPP_VERIFY_TOKEN` | Optional | Webhook verification string set in the Meta developer portal. | `your-verify-token` |
| `WHATSAPP_ACCESS_TOKEN` | Optional | Access token for the WhatsApp cloud API. | `EAAG...` |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | Phone number ID registered with WhatsApp Cloud API. | `123456789012345` |
| `WHATSAPP_APP_SECRET` | Required for WhatsApp webhooks | Meta app secret used to verify `X-Hub-Signature-256` on incoming webhook events. | `your-whatsapp-app-secret` |
| `SLACK_BOT_TOKEN` | Optional | Bot token to trigger Slack workflows. | `xoxb-your-token-here` |
| `SLACK_SIGNING_SECRET` | Optional | Signing secret to verify incoming webhook payloads from Slack. | `slack_signing_secret` |
| `SLACK_DEMO_CHANNEL_ID` | Optional | Channel ID where Slack reports/alerts are pushed. | `C0123456789` |

#### 6. Default Settings & Metadata
Optional default values and metadata used for fallback behavior or logging.

| Variable | Status | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `DEFAULT_BUSINESS_ID` | Optional | Fallback business ID if not specified in session context. | `550e8400-e29b-41d4-a716-446655440000` |
| `GITHUB_REPO` | Optional | Repository path used for reporting issues or logging features. | `mohitkumhar/intelligent-business-agent` |

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

Set `TELEGRAM_BOT_TOKEN` and a high-entropy `TELEGRAM_WEBHOOK_SECRET`, then configure your Telegram bot webhook to POST updates to:

```text
https://<your-agent-domain>/api/v1/telegram/webhook
```

Register the same secret with Telegram so each update includes `X-Telegram-Bot-Api-Secret-Token`:

```bash
curl -X POST "https://api.telegram.org/bot<your-token>/setWebhook" \
  -d "url=https://<your-agent-domain>/api/v1/telegram/webhook" \
  -d "secret_token=<your-telegram-webhook-secret>"
```

Text messages and captions are forwarded to the AI agent. Photo, document, or voice updates without captions receive a helpful fallback message instead of failing silently.

---

## 🤝 Contributing — GSSoC Guide

Welcome to GirlScript Summer of Code 2025! 🎉 We're excited to have you. Please read our full [Contributing Guide](./CONTRIBUTING.md) for detailed instructions on how to set up the project, run it locally, and submit pull requests.

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
