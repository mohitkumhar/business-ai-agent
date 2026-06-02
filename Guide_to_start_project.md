## 🚀 Run Project Locally (Dev Environment)

### 1️⃣ Install Requirements

* Install Docker Desktop (or Docker Engine + Compose)
* Install Git

Verify:
docker --version
docker compose version

### 2️⃣ Clone Repository
git clone <repo-url>
cd intelligent-business-agent

### 3️⃣ Start All Services
docker compose up 

### 4️⃣ Configuring API URLs (Important)

If you are running the project for the first time or in a non-standard environment, ensure your environment variables are set correctly so the frontend can talk to the backend.

| Variable | Recommended Value | Description |
|----------|-------------------|-------------|
| `VITE_API_URL` | `http://localhost:5000` | Used by the **Landing Page** to connect to the Agent. |
| `AGENT_API_URL` | `http://backend:5000` | Used by the **Dashboard** (Next.js) inside Docker. |

### 5️⃣ Access Services
Frontend:

http://localhost:5173


### Stop Services
docker compose down

