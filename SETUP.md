# ScalperAI — Full Setup Guide

Complete deployment guide for all four components of the platform.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Windows VPS                                                    │
│  ┌─────────────────┐                                           │
│  │  MetaTrader 5   │◄──── Your broker account                 │
│  │  Terminal       │                                           │
│  └────────┬────────┘                                           │
│           │ Python SDK                                          │
│  ┌────────▼────────┐                                           │
│  │  MT5 Bridge     │  :9000  (FastAPI + auth middleware)       │
│  └────────┬────────┘                                           │
└───────────┼─────────────────────────────────────────────────────┘
            │ HTTP (X-Bridge-Secret)
┌───────────▼─────────────────────────────────────────────────────┐
│  Linux Server / Cloud VPS                                       │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌───────────────┐  │
│  │  AI Engine   │────►│    Redis     │────►│   Backend     │  │
│  │  (Python)    │     │   Queue      │     │  (FastAPI)    │  │
│  └──────────────┘     └──────────────┘     └───────┬───────┘  │
│                                                     │           │
│                                             ┌───────▼───────┐  │
│                                             │  PostgreSQL   │  │
│                                             └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │ REST + WebSocket
┌───────────▼─────────────────────────────────────────────────────┐
│  Frontend (Next.js)  — localhost:3000 or Vercel                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow:**
`MT5 candles → AI Engine → signal scored → Redis queue → Backend dispatcher → MT5 Bridge executes order → Trade recorded in DB`

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Windows VPS | Windows 10/11 or Server 2019+, Python 3.11+, MT5 terminal installed |
| Linux Server | Ubuntu 22.04+, Python 3.11+, Docker (for Postgres + Redis) |
| Frontend | Node.js 20+, npm 10+ |
| MT5 Terminal | Logged in to your broker account before starting bridge |

---

## Part 1 — Windows VPS: MT5 Bridge

### 1.1 Install Python and Git

Open **PowerShell as Administrator**:

```powershell
# Check Python version (need 3.11+)
python --version

# If not installed, download from https://python.org
# ✅ During install: check "Add Python to PATH"

# Install git
winget install Git.Git
```

### 1.2 Clone the repository

```powershell
git clone https://github.com/jigwemoh/scalper-saas.git C:\scalper-saas
cd C:\scalper-saas\apps\mt5-bridge
```

### 1.3 Create virtual environment and install dependencies

```powershell
python -m venv .venv

# If you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 1.4 Configure your MT5 credentials

Edit `start.ps1` with your real values:

```powershell
notepad C:\scalper-saas\apps\mt5-bridge\start.ps1
```

```powershell
# ─── start.ps1 ───────────────────────────────────────────────────
$env:MT5_BRIDGE_SECRET = "choose-a-strong-secret-32-chars+"   # 🔑 Must match backend .env
$env:MT5_LOGIN         = "12345678"           # Your MT5 account number
$env:MT5_PASSWORD      = "YourBrokerPassword" # Your MT5 account password
$env:MT5_SERVER        = "ICMarkets-Live01"   # Your broker server name
$env:MT5_MAGIC_NUMBER  = "20250101"           # Unique tag for your orders
$env:CORS_ORIGINS      = "http://YOUR-LINUX-SERVER-IP:8000"

Write-Host "Starting MT5 Bridge on port 9000..."
uvicorn app:app --host 0.0.0.0 --port 9000 --workers 1
```

> **How to find your MT5 server name:**
> Open MT5 terminal → File → Open Account → look at the server dropdown.
> Examples: `ICMarkets-Live01`, `Pepperstone-Live02`, `XM.COM-Real3`, `FusionMarkets-Live`

### 1.5 Open Windows Firewall port

```powershell
New-NetFirewallRule `
  -DisplayName "MT5 Bridge Port 9000" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 9000 `
  -Action Allow
```

### 1.6 Start the bridge (manual test first)

Make sure MT5 terminal is **open and logged in**, then:

```powershell
cd C:\scalper-saas\apps\mt5-bridge
.\.venv\Scripts\Activate.ps1
.\start.ps1
```

You should see:
```
Starting MT5 Bridge on port 9000...
INFO: MT5 initialized. version=(...) terminal_info=(...)
INFO: Uvicorn running on http://0.0.0.0:9000
```

Test in browser on the VPS: `http://localhost:9000/api/health/system`

Expected response:
```json
{"mt5_available": true, "initialized": true}
```

### 1.7 Install as a Windows Service (auto-starts on reboot)

```powershell
# Install NSSM service manager
winget install NSSM.NSSM

# Register the bridge as a service
nssm install MT5Bridge powershell.exe
nssm set MT5Bridge AppParameters "-ExecutionPolicy Bypass -File C:\scalper-saas\apps\mt5-bridge\start.ps1"
nssm set MT5Bridge AppDirectory "C:\scalper-saas\apps\mt5-bridge"
nssm set MT5Bridge AppEnvironmentExtra `
    "MT5_BRIDGE_SECRET=your-strong-secret-here" `
    "MT5_LOGIN=12345678" `
    "MT5_PASSWORD=YourBrokerPassword" `
    "MT5_SERVER=ICMarkets-Live01" `
    "MT5_MAGIC_NUMBER=20250101"
nssm set MT5Bridge Start SERVICE_AUTO_START
nssm set MT5Bridge AppStdout "C:\scalper-saas\logs\bridge-stdout.log"
nssm set MT5Bridge AppStderr "C:\scalper-saas\logs\bridge-stderr.log"

# Create log directory
mkdir C:\scalper-saas\logs

# Start the service
nssm start MT5Bridge

# Check status
nssm status MT5Bridge   # Should say: SERVICE_RUNNING
```

---

## Part 2 — Linux Server: Backend + AI Engine

### 2.1 Install system dependencies

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11, git, Docker
sudo apt install -y python3.11 python3.11-venv python3-pip git curl

# Install Docker + Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2.2 Clone the repository

```bash
git clone https://github.com/jigwemoh/scalper-saas.git ~/scalper-saas
cd ~/scalper-saas
```

### 2.3 Start PostgreSQL and Redis via Docker

```bash
cd docker
docker compose up postgres redis -d

# Verify containers are running
docker ps
# Should show: scalper_postgres and scalper_redis
```

### 2.4 Configure the backend

```bash
cd ~/scalper-saas/apps/backend
cp .env.example .env
nano .env
```

Fill in your `.env`:

```env
# Database (Docker default)
DATABASE_URL=postgresql+asyncpg://scalper:scalper_dev_pass@localhost:5432/scalper_saas

# Redis (Docker default)
REDIS_URL=redis://localhost:6379/0

# JWT — generate a strong random key
JWT_SECRET_KEY=your-32-char-random-string-here

# MT5 Bridge — must match what you set on the Windows VPS
MT5_BRIDGE_URL=http://YOUR-WINDOWS-VPS-IP:9000
MT5_BRIDGE_SECRET=your-strong-secret-here    # Same value as in start.ps1

# Paystack (payment processor — leave empty for dev)
PAYSTACK_SECRET_KEY=sk_live_your_key_here
PAYSTACK_PUBLIC_KEY=pk_live_your_key_here

# App
APP_ENV=production
CORS_ORIGINS=http://YOUR-FRONTEND-DOMAIN,http://localhost:3000
```

> **Generate a strong JWT secret:**
> ```bash
> python3 -c "import secrets; print(secrets.token_hex(32))"
> ```

### 2.5 Set up Python virtual environment and run migrations

```bash
cd ~/scalper-saas/apps/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run all database migrations
alembic upgrade head
```

You should see:
```
INFO  [alembic.runtime.migration] Running upgrade -> 001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, add close_reason...
```

### 2.6 Configure the AI engine

```bash
cd ~/scalper-saas/apps/ai-engine
cp .env.example .env
nano .env
```

```env
MT5_BRIDGE_URL=http://YOUR-WINDOWS-VPS-IP:9000
MT5_BRIDGE_SECRET=your-strong-secret-here    # Same value as in start.ps1
REDIS_URL=redis://localhost:6379/0
BACKEND_URL=http://localhost:8000
AI_ENGINE_SECRET=choose-an-engine-secret     # Internal secret for AI→backend calls
```

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.7 Start backend and AI engine

**Terminal 1 — Backend:**
```bash
cd ~/scalper-saas/apps/backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — AI Engine:**
```bash
cd ~/scalper-saas/apps/ai-engine
source .venv/bin/activate
python main.py
```

You should see the AI engine scanning every 60 seconds:
```
INFO  scan_job: Scanning 3 symbols...
INFO  scan_job: SIGNAL: BUY EURUSD prob=0.721 regime=trending_up session=london
INFO  scan_job: Signal pushed to Redis queue: BUY EURUSD
```

### 2.8 Run as systemd services (auto-start on reboot)

**Backend service:**
```bash
sudo nano /etc/systemd/system/scalper-backend.service
```

```ini
[Unit]
Description=Scalper SaaS Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/scalper-saas/apps/backend
Environment="PATH=/home/ubuntu/scalper-saas/apps/backend/.venv/bin"
EnvironmentFile=/home/ubuntu/scalper-saas/apps/backend/.env
ExecStart=/home/ubuntu/scalper-saas/apps/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**AI Engine service:**
```bash
sudo nano /etc/systemd/system/scalper-ai.service
```

```ini
[Unit]
Description=Scalper AI Engine
After=network.target scalper-backend.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/scalper-saas/apps/ai-engine
Environment="PATH=/home/ubuntu/scalper-saas/apps/ai-engine/.venv/bin"
EnvironmentFile=/home/ubuntu/scalper-saas/apps/ai-engine/.env
ExecStart=/home/ubuntu/scalper-saas/apps/ai-engine/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable scalper-backend scalper-ai
sudo systemctl start scalper-backend scalper-ai

# Check status
sudo systemctl status scalper-backend
sudo systemctl status scalper-ai

# View live logs
sudo journalctl -u scalper-backend -f
sudo journalctl -u scalper-ai -f
```

---

## Part 3 — Frontend

### 3.1 Local development

```bash
cd ~/scalper-saas/apps/frontend
cp .env.local.example .env.local
nano .env.local
```

```env
NEXT_PUBLIC_API_URL=http://YOUR-LINUX-SERVER-IP:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://YOUR-LINUX-SERVER-IP:8000/ws
API_URL=http://YOUR-LINUX-SERVER-IP:8000
```

```bash
npm install
npm run dev       # http://localhost:3000
```

### 3.2 Deploy to Vercel (production)

```bash
# Install Vercel CLI
npm install -g vercel

cd ~/scalper-saas/apps/frontend
vercel

# Follow the prompts, then set environment variables in Vercel dashboard:
# NEXT_PUBLIC_API_URL  = https://api.yourdomain.com/api/v1
# NEXT_PUBLIC_WS_URL   = wss://api.yourdomain.com/ws
# API_URL              = https://api.yourdomain.com
```

---

## Part 4 — Environment Variables Reference

### `apps/mt5-bridge/start.ps1` (Windows VPS)

| Variable | Required | Description |
|----------|----------|-------------|
| `MT5_BRIDGE_SECRET` | ✅ | Shared secret — must match backend `MT5_BRIDGE_SECRET` |
| `MT5_LOGIN` | ✅ | MT5 account number (digits only) |
| `MT5_PASSWORD` | ✅ | MT5 account password |
| `MT5_SERVER` | ✅ | Broker server name (e.g. `ICMarkets-Live01`) |
| `MT5_MAGIC_NUMBER` | ✅ | Unique integer to tag your orders (e.g. `20250101`) |
| `CORS_ORIGINS` | Optional | Backend server IP allowed to call bridge |

### `apps/backend/.env` (Linux Server)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `JWT_SECRET_KEY` | ✅ | Random 32+ char string for signing JWT tokens |
| `MT5_BRIDGE_URL` | ✅ | `http://YOUR-WINDOWS-VPS-IP:9000` |
| `MT5_BRIDGE_SECRET` | ✅ | Must match `MT5_BRIDGE_SECRET` in `start.ps1` |
| `PAYSTACK_SECRET_KEY` | Optional | Paystack live secret key for payments |
| `APP_ENV` | ✅ | `production` or `development` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed frontend origins |

### `apps/ai-engine/.env` (Linux Server)

| Variable | Required | Description |
|----------|----------|-------------|
| `MT5_BRIDGE_URL` | ✅ | `http://YOUR-WINDOWS-VPS-IP:9000` |
| `MT5_BRIDGE_SECRET` | ✅ | Must match `MT5_BRIDGE_SECRET` in `start.ps1` |
| `REDIS_URL` | ✅ | Redis connection string |
| `BACKEND_URL` | ✅ | `http://localhost:8000` |
| `AI_ENGINE_SECRET` | ✅ | Internal secret for AI engine → backend API calls |

### `apps/frontend/.env.local`

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL visible to browser |
| `NEXT_PUBLIC_WS_URL` | ✅ | WebSocket URL visible to browser |
| `API_URL` | ✅ | Backend URL for server-side Next.js calls |

---

## Part 5 — Verify Everything is Working

### Check 1: MT5 Bridge responds

```bash
# From your Linux server
curl -H "X-Bridge-Secret: your-secret-here" \
     http://YOUR-VPS-IP:9000/api/mt5/account
```
Expected: `{"equity": 10000.0, "balance": 10000.0, ...}`

### Check 2: Backend health

```bash
curl http://localhost:8000/health
```
Expected: `{"status": "ok", "version": "1.0.0"}`

### Check 3: AI engine is scanning

```bash
sudo journalctl -u scalper-ai -f
```
Expected every 60s:
```
INFO scan_job: Scanning 3 symbols...
```

### Check 4: Signals flowing to Redis

```bash
redis-cli LLEN signals:pending   # Will be 0 if dispatcher consumed them
redis-cli SUBSCRIBE signals:*    # Watch for published signals
```

### Check 5: Frontend loads

Visit `http://localhost:3000` — you should see the login page.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| Bridge: `MT5 not available` | MT5 Python pkg only runs on Windows | Ensure bridge runs on Windows VPS, not Linux |
| Bridge: `MT5 initialize failed` | MT5 terminal not open | Open MT5 terminal on VPS, log in to your account |
| Bridge: 401 Unauthorized | Secret mismatch | Make sure `MT5_BRIDGE_SECRET` is identical on both VPS and backend |
| Backend: `ModuleNotFoundError` | Venv not activated | Run `source .venv/bin/activate` before uvicorn |
| Backend: `relation does not exist` | Migrations not run | Run `alembic upgrade head` |
| AI engine: no signals | Bridge unreachable | Check VPS IP and firewall port 9000 |
| AI engine: no signals | Models not trained yet | Normal on first run — signals generate after 24h when first retrain completes |
| Frontend: 404 on API calls | Wrong `NEXT_PUBLIC_API_URL` | Check `.env.local` — no trailing slash |

---

## Security Checklist Before Going Live

- [ ] `MT5_BRIDGE_SECRET` is a strong random string (not `dev-bridge-secret`)
- [ ] `JWT_SECRET_KEY` is at least 32 random characters
- [ ] Port 9000 on VPS is only accessible from your Linux server IP (not `0.0.0.0` publicly)
- [ ] PostgreSQL port 5432 is not exposed to the public internet
- [ ] `APP_ENV=production` is set in backend `.env`
- [ ] MT5 terminal is set to auto-start on Windows VPS reboot
- [ ] NSSM service for MT5 Bridge is configured to auto-start

---

## Updating the Platform

```bash
# On Linux server
cd ~/scalper-saas
git pull

# Restart services
sudo systemctl restart scalper-backend scalper-ai

# If DB models changed, run migrations
cd apps/backend && source .venv/bin/activate && alembic upgrade head
```

```powershell
# On Windows VPS
cd C:\scalper-saas
git pull

# Restart the bridge service
nssm restart MT5Bridge
```
