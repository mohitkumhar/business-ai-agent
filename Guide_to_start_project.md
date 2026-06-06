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
cd intelligent-business-agent
```

### 3️⃣ Start All Services

```bash
docker compose up
```

### 4️⃣ Access Services

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

**Purpose:** Defines the backend API endpoint used by the Landing Page frontend for onboarding requests and API communication.

### Used In

* landing-page/src/routes/get-started.tsx
* .env.example
* docker-compose.yml
  
### Local Development

The default value provided in `.env.example` is:

```env
VITE_API_URL=http://localhost:5000
```

### Docker Deployment

The default Docker configuration in `docker-compose.yml` uses:

```env
VITE_API_URL=http://backend:5000
```

### Production Deployment

```env
VITE_API_URL=https://your-api-domain.com
```

---

## AGENT_API_URL

**Purpose:** Defines the backend API endpoint used by the Dashboard, backend proxy routes, and agent services.

### Used In

* dashboard/next.config.ts
* dashboard/src/app/api/chat/route.ts
* dashboard/src/app/api/employees/route.ts
* dashboard/src/app/api/escalate/route.ts
* web/app.py
* .env.example
* docker-compose.yml
  
### Local Development

The default value provided in `.env.example` is:

```env
AGENT_API_URL=http://localhost:5000
```

### Docker Deployment

The default Dashboard Docker configuration uses:

```env
AGENT_API_URL=http://backend:5000
```

### Production Deployment

```env
AGENT_API_URL=https://your-api-domain.com
```

---

## VITE_AGENT_API_URL

**Purpose:** Optional override variable used by the Landing Page. When provided, it takes priority over `VITE_API_URL`.

### Used In

* `landing-page/src/constants.ts`
* `landing-page/src/vite-env.d.ts`

### Example

```env
VITE_AGENT_API_URL=http://localhost:5000
```

---

## How Services Communicate

```text
Landing Page
      |
      | VITE_API_URL / VITE_AGENT_API_URL
      v
Flask Backend

Dashboard
      |
      | AGENT_API_URL
      v
Flask Backend
```

---

## Common Configuration Mistakes

### API Requests Fail

Verify that `VITE_API_URL`, `VITE_AGENT_API_URL`, and `AGENT_API_URL` point to the correct backend service.

### Docker Containers Cannot Connect

Inside Docker containers, use:

```env
http://backend:5000
```

instead of:

```env
http://localhost:5000
```

### Production API Errors

Check:

* Production API URL
* CORS configuration
* Environment variable values
* Reverse proxy settings (if applicable)

---

## Troubleshooting

1. Confirm environment variables are set correctly.
2. Restart containers after updating `.env` values.
3. Verify the backend service is running.
4. Test API endpoints directly before debugging frontend issues.
5. Check Docker logs for networking or startup errors.
6. Ensure frontend and backend services use matching API URLs.

---

## Quick Reference

| Variable           | Local Development     | Docker              | Production                  |
| ------------------ | --------------------- | ------------------- | --------------------------- |
| VITE_API_URL       | http://localhost:5000 | http://backend:5000 | https://your-api-domain.com |
| AGENT_API_URL      | http://localhost:5000 | http://backend:5000 | https://your-api-domain.com |
| VITE_AGENT_API_URL | Optional Override     | Optional Override   | Optional Override           |
