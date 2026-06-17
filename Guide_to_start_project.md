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

### 3️⃣ Setup Environment Variables
Copy the environment variables template to the project root directory:
```bash
cp .env.example .env
```
Open the newly created `.env` file and populate the required fields (e.g., database credentials and `GROQ_API_KEY`). For a detailed breakdown of all variables, refer to the [Environment Variables Guide in README.md](README.md#🔐-environment-variables).

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
docker compose up 

### 5️⃣ Access Services
Frontend:

http://localhost:5173


### Stop Services
docker compose down
