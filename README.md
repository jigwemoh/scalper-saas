# ScalperAI — MT5 Signal SaaS

AI-driven M1/M5 scalping signal platform for MetaTrader 5. Subscribers receive
signals via API key (compatible with MT5 EAs).

## Architecture

```
Windows VPS (MT5 Bridge)  →  Linux VPS (Backend + AI Engine)  →  Vercel (Next.js)
                                      ↑
                               User MT5 EA (polls signals)
```

## Quick Start (Local Dev)

### 1. Start infrastructure
```bash
cd docker
cp ../apps/backend/.env.example ../apps/backend/.env
docker compose up postgres redis -d
```

### 2. Run backend
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

### 3. Run AI engine (needs MT5 bridge running)
```bash
cd apps/ai-engine
cp .env.example .env
pip install -r requirements.txt
python main.py
```

### 4. Run frontend
```bash
cd apps/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### 5. MT5 Bridge (Windows VPS only)
```powershell
cd apps/mt5-bridge
pip install -r requirements.txt
.\start.ps1
```

## Subscription Tiers

| Plan | Price | Risk/Trade | Max Lots |
|------|-------|-----------|----------|
| Starter | $49/mo | 0.5% | 0.1 |
| Pro | $99/mo | 1.5% | 1.0 |
| Elite | $199/mo | 2.5% | 5.0 |

## Kill Switches

| Trigger | Action |
|---------|--------|
| -6% daily | Soft pause |
| -8% daily | Hard kill (resumes next day) |
| -12% weekly | Weekly kill |

## API Key Usage (MT5 EA)

```
GET https://api.yoursite.com/api/v1/signals/latest?symbol=EURUSD
Headers: X-API-Key: sk_your_key_here
```

## Symbols
- EURUSD, GBPUSD, XAUUSD (configurable in `ai-engine/strategy/signal_generator.py`)

## Testing
```bash
# Backend
cd apps/backend && pytest tests/

# AI Engine
cd apps/ai-engine && pytest tests/
```
