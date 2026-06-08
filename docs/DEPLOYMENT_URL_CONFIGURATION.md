# 🚀 Deployment URL Configuration Guide

This guide explains how to configure API URLs across the **ProfitPilot** frontend and backend services for local development, Docker deployments, and production environments.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Key Environment Variables](#key-environment-variables)
3. [Local Development Setup](#local-development-setup)
4. [Docker Deployment Setup](#docker-deployment-setup)
5. [Production Deployment Setup](#production-deployment-setup)
6. [How Frontend Communicates with Backend](#how-frontend-communicates-with-backend)
7. [Common Mistakes & Troubleshooting](#common-mistakes--troubleshooting)
8. [Quick Reference Table](#quick-reference-table)

---

## Overview

ProfitPilot consists of multiple services that need to communicate with each other:
API URLs are configured differently depending on the environment:

| Environment | URL Format |
|---|---|
| Local Dev | `http://localhost:PORT` |
| Docker | `http://service-name:PORT` |
| Production | `https://your-domain.com` |

---

## Key Environment Variables

### `VITE_API_URL`
**Used by:** Landing Page (Vite frontend)  
**Purpose:** Points the Vite landing page to the Flask backend API

```bash
# Local Development
VITE_API_URL=http://localhost:5000

# Docker
VITE_API_URL=http://backend:5000

# Production
VITE_API_URL=https://api.your-domain.com
```

---

### `AGENT_API_URL`
**Used by:** Next.js Dashboard (server-side)  
**Purpose:** Server-side URL for Dashboard → Flask backend communication

```bash
# Local Development
AGENT_API_URL=http://localhost:5000

# Docker
AGENT_API_URL=http://backend:5000

# Production
AGENT_API_URL=https://api.your-domain.com
```

---

### `NEXT_PUBLIC_AGENT_API_URL`
**Used by:** Next.js Dashboard (client-side/browser)  
**Purpose:** Browser-side URL for direct API calls from the user's browser

```bash
# Local Development
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000

# Docker (must be accessible from user's browser, not Docker network)
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000

# Production
NEXT_PUBLIC_AGENT_API_URL=https://api.your-domain.com
```

> ⚠️ **Important:** `NEXT_PUBLIC_*` variables are exposed to the browser. Never put secrets here.

---

### `NEXT_PUBLIC_LANDING_URL`
**Used by:** Next.js Dashboard  
**Purpose:** URL of the Vite landing/onboarding page

```bash
# Local Development
NEXT_PUBLIC_LANDING_URL=http://localhost:5173

# Docker
NEXT_PUBLIC_LANDING_URL=http://localhost:5173

# Production
NEXT_PUBLIC_LANDING_URL=https://your-domain.com
```

---

### `DATABASE_URL`
**Used by:** Flask backend  
**Purpose:** PostgreSQL connection string

```bash
# Local Development
DATABASE_URL=postgresql://profitpilot_dev:password@localhost:5432/test_db

# Docker (hostname must be 'db' — Docker service name)
DATABASE_URL=postgresql://profitpilot_dev:password@db:5432/test_db

# Production
DATABASE_URL=postgresql://user:password@your-db-host:5432/dbname
```

---

## Local Development Setup

Use this when running services directly on your machine (without Docker).

### Step 1 — Copy env file

```bash
cp .env.example .env
```

Also copy to service directories:
```bash
cp .env.example agent_code/.env
cp .env.example dashboard/.env
cp .env.example landing-page/.env
```

### Step 2 — Configure URLs for local

Open `.env` and set:

```bash
# Backend
AGENT_API_URL=http://localhost:5000
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000

# Frontend
VITE_API_URL=http://localhost:5000
NEXT_PUBLIC_LANDING_URL=http://localhost:5173
NEXT_PUBLIC_VIEWER_URL=http://localhost:5173
NEXTAUTH_URL=http://localhost:3000

# Database (localhost for local setup)
DATABASE_URL=postgresql://profitpilot_dev:yourpassword@localhost:5432/test_db
```

### Step 3 — Start services manually

```bash
# Terminal 1 — Flask Backend
cd agent_code
python app.py

# Terminal 2 — Next.js Dashboard
cd dashboard
npm run dev

# Terminal 3 — Vite Landing Page
cd landing-page
npm run dev
```

### Service URLs (Local)

| Service | URL |
|---|---|
| Flask Backend | http://localhost:5000 |
| Next.js Dashboard | http://localhost:3000 |
| Vite Landing Page | http://localhost:5173 |
| pgAdmin | http://localhost:5050 |

---

## Docker Deployment Setup

Use this when running all services via Docker Compose.

### Step 1 — Copy env file

```bash
cp .env.example .env
```

### Step 2 — Configure URLs for Docker

Open `.env` and set:

```bash
# Backend (use Docker service name 'backend')
AGENT_API_URL=http://backend:5000
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000  # browser uses localhost

# Frontend
VITE_API_URL=http://backend:5000
NEXT_PUBLIC_LANDING_URL=http://localhost:5173
NEXTAUTH_URL=http://localhost:3000

# Database (use Docker service name 'db')
DATABASE_URL=postgresql://profitpilot_dev:yourpassword@db:5432/test_db

# Monitoring
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
```

### Step 3 — Start with Docker Compose

```bash
docker compose up
```

### Service URLs (Docker)

| Service | URL |
|---|---|
| Flask Backend | http://localhost:5000 |
| Next.js Dashboard | http://localhost:3000 |
| Vite Landing Page | http://localhost:5173 |
| pgAdmin | http://localhost:5050 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

---

## Production Deployment Setup

Use this when deploying to a cloud server or VPS.

### Step 1 — Set real domain URLs

```bash
# Backend API
AGENT_API_URL=https://api.your-domain.com
NEXT_PUBLIC_AGENT_API_URL=https://api.your-domain.com
VITE_API_URL=https://api.your-domain.com

# Frontend
NEXT_PUBLIC_LANDING_URL=https://your-domain.com
NEXT_PUBLIC_VIEWER_URL=https://your-domain.com
NEXTAUTH_URL=https://dashboard.your-domain.com

# Database
DATABASE_URL=postgresql://user:strongpassword@your-db-host:5432/dbname
```

### Step 2 — Use strong secrets

```bash
# Generate JWT secret
openssl rand -hex 32

# Generate encryption secret (must be exactly 32 chars)
openssl rand -hex 16
```

---

## How Frontend Communicates with Backend
### Key Rule:
- **Server-side code** (Next.js API routes) → use `AGENT_API_URL` (Docker service name works)
- **Client-side code** (browser) → use `NEXT_PUBLIC_AGENT_API_URL` (must be `localhost` or real domain)

---

## Common Mistakes & Troubleshooting

### ❌ `Connection refused` on API calls

**Cause:** Wrong hostname in URL  
**Fix:**
- Local → use `localhost`
- Docker → use service name (`backend`, `db`)

---

### ❌ Dashboard can't reach backend in Docker

**Cause:** Using `localhost` instead of Docker service name  
**Fix:**
```bash
AGENT_API_URL=http://backend:5000  # ✅ correct for Docker
AGENT_API_URL=http://localhost:5000  # ❌ wrong for Docker server-side
```

---

### ❌ Browser can't reach API in Docker

**Cause:** Using Docker service name in `NEXT_PUBLIC_*` variable  
**Fix:**
```bash
NEXT_PUBLIC_AGENT_API_URL=http://localhost:5000  # ✅ browser uses localhost
NEXT_PUBLIC_AGENT_API_URL=http://backend:5000   # ❌ browser can't resolve 'backend'
```

---

### ❌ Database connection fails in Docker

**Cause:** Using `localhost` instead of `db` for hostname  
**Fix:**
```bash
DATABASE_URL=postgresql://user:pass@db:5432/test_db      # ✅ Docker
DATABASE_URL=postgresql://user:pass@localhost:5432/test_db  # ✅ Local only
```

---

### ❌ `ENCRYPTION_SECRET must be 32 characters`

**Fix:**
```bash
openssl rand -hex 16  # generates exactly 32 hex characters
```

---

## Quick Reference Table

| Variable | Local Dev | Docker | Production |
|---|---|---|---|
| `VITE_API_URL` | `http://localhost:5000` | `http://backend:5000` | `https://api.domain.com` |
| `AGENT_API_URL` | `http://localhost:5000` | `http://backend:5000` | `https://api.domain.com` |
| `NEXT_PUBLIC_AGENT_API_URL` | `http://localhost:5000` | `http://localhost:5000` | `https://api.domain.com` |
| `NEXT_PUBLIC_LANDING_URL` | `http://localhost:5173` | `http://localhost:5173` | `https://domain.com` |
| `DATABASE_URL` hostname | `localhost` | `db` | your-db-host |
| `PROMETHEUS_URL` | `http://localhost:9090` | `http://prometheus:9090` | your-prometheus-url |
| `LOKI_URL` | `http://localhost:3100` | `http://loki:3100` | your-loki-url |

---

*For more setup details, refer to [Guide_to_start_project.md](../Guide_to_start_project.md) and [README.md](../README.md).*