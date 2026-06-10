## 🚀 Run Project Locally (Dev Environment)

### 1️⃣ Install Requirements

* Install Docker Desktop (or Docker Engine + Compose)
* Install Git

Verify installation:

```bash
docker --version
docker compose version
```

### 2️⃣ Clone Repository

```bash
git clone <repo-url>
cd business-ai-agent
```

### 3️⃣ Setup Environment Variables

Copy the environment variables template to the project root directory:

```bash
cp .env.example .env
```

Open the newly created `.env` file and populate the required fields (e.g., database credentials and `GROQ_API_KEY`).

For a detailed breakdown of all variables, refer to the Environment Variables Guide in README.md.

Generate local-only database and pgAdmin passwords before starting Docker Compose:

```bash
POSTGRES_PASSWORD_VALUE="$(openssl rand -hex 24)"
PGADMIN_PASSWORD_VALUE="$(openssl rand -hex 24)"

perl -0pi -e "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD_VALUE}|" .env
perl -0pi -e "s|DATABASE_URL=.*|DATABASE_URL=postgresql://profitpilot_dev:${POSTGRES_PASSWORD_VALUE}\@db:5432/test_db|" .env
perl -0pi -e "s|PGADMIN_DEFAULT_EMAIL=.*|PGADMIN_DEFAULT_EMAIL=you\@example.com|" .env
perl -0pi -e "s|PGADMIN_DEFAULT_PASSWORD=.*|PGADMIN_DEFAULT_PASSWORD=${PGADMIN_PASSWORD_VALUE}|" .env
```

Docker Compose binds PostgreSQL and pgAdmin to localhost by default and stops if placeholder credentials are still present.

### 4️⃣ Start All Services

```bash
docker compose up
```

### 5️⃣ Access Services

Frontend:

```text
http://localhost:5173
```

### Stop Services

```bash
docker compose down
```

---

# 🌐 API URL Configuration Guide

This guide explains how API URLs are configured across the Landing Page, Dashboard, and Backend services for local development, Docker deployments, and production environments.

## VITE_API_URL

**Purpose:** Defines the backend API endpoint used by the Landing Page onboarding flow.

### Used In

* `landing-page/src/routes/get-started.tsx`
* `docker-compose.yml`

### Local Development

```env
VITE_API_URL=http://localhost:5000
```

### Docker Deployment

For browser-accessible Docker environments:

```env
VITE_API_URL=http://localhost:5000
```

### Production Deployment

```env
VITE_API_URL=https://your-api-domain.com
```

---

## VITE_AGENT_API_URL

**Purpose:** Optional Landing Page override. When provided, it takes priority over `VITE_API_URL`.

### Used In

* `landing-page/src/constants.ts`
* `landing-page/src/vite-env.d.ts`

### Typical Configuration

```env
VITE_AGENT_API_URL=http://localhost:5000
```

### Production Deployment

```env
VITE_AGENT_API_URL=https://your-api-domain.com
```

---

## AGENT_API_URL

**Purpose:** Server-side API endpoint used by Dashboard API routes and backend proxy services.

### Used In

* `dashboard/next.config.ts`
* `dashboard/src/app/api/chat/route.ts`
* `dashboard/src/app/api/employees/route.ts`
* `dashboard/src/app/api/escalate/route.ts`
* `web/app.py`
* `.env.example`
* `docker-compose.yml`

### Local Development

```env
AGENT_API_URL=http://localhost:5000
```

> Note: `web/app.py` falls back to `http://127.0.0.1:5000` if `AGENT_API_URL` is not set.

### Docker Deployment

```env
AGENT_API_URL=http://backend:5000
```

### Production Deployment

```env
AGENT_API_URL=https://your-api-domain.com
```

---

## NEXT_PUBLIC_AGENT_API_URL

**Purpose:** Optional public-facing API URL used by the Dashboard frontend.

### Used In

* `dashboard/src/lib/publicUrls.ts`
* `.env.example`

### Local Development

```env
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000
```

### Docker Deployment

```env
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000
```

### Production Deployment

```env
NEXT_PUBLIC_AGENT_API_URL=https://your-api-domain.com
```

---

## How Services Communicate

```text
Landing Page
      |
      | VITE_API_URL / VITE_AGENT_API_URL
      v
Flask Backend

Dashboard Frontend
      |
      | NEXT_PUBLIC_AGENT_API_URL (optional)
      v
Next.js API Routes
      |
      | AGENT_API_URL
      v
Flask Backend
```

---

## Quick Reference

| Variable | Local Development | Docker | Production |
|-----------|-----------|-----------|-----------|
| VITE_API_URL | http://localhost:5000 | http://localhost:5000 | https://your-api-domain.com |
| VITE_AGENT_API_URL | Optional Override | Optional Override | Optional Override |
| AGENT_API_URL | http://localhost:5000 | http://backend:5000 | https://your-api-domain.com |
| NEXT_PUBLIC_AGENT_API_URL | http://localhost:5000 | http://localhost:5000 | https://your-api-domain.com |
