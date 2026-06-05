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

### 4️⃣ Start All Services
docker compose up 

### 5️⃣ Access Services
Frontend:

http://localhost:5173


### Stop Services
docker compose down

