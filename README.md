# CostForge

**Version:** v2.0  
**Status:** Production Ready  
**Repository:** https://github.com/OneByJorah/CostForge

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Service Management](#service-management)
- [Admin Panel](#admin-panel)
- [CI/CD & Deployment](#cicd--deployment)
- [Security](#security)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [License](#license)
- [Author](#author)

---

## Overview

CostForge is a **cloud cost estimation and pricing dashboard** that aggregates pricing catalogs, ingests usage data, and presents cost breakdowns through a dark-themed, single-page dashboard. Built for operators who need quick visibility into cloud/LLM spend without leaving their internal tooling.

**Core philosophy:** Self-hosted, zero external dependencies, zero secrets in git.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TAILSCALE NETWORK                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      COSTFORGE STACK                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  COSTFORGE FRONTEND (nginx:8090)                           │  │
│  │    Dark-themed SPA dashboard                                │  │
│  │    /api/* → proxied to backend                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  COSTFORGE BACKEND (FastAPI:8000)                          │  │
│  │    /healthz          - Health check                         │  │
│  │    /ingest           - Accept usage data (POST)             │  │
│  │    /api/usage        - Query raw usage (GET)                │  │
│  │    /api/summary      - Aggregated cost breakdown (GET)      │  │
│  │    /                 - Serves frontend (dev)                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│        ┌─────────────────────┼─────────────────────┐             │
│        ▼                     ▼                     ▼             │
│  ┌───────────┐         ┌───────────┐         ┌───────────┐     │
│  │  PRICING  │         │  USAGE    │         │  ADAPTERS │     │
│  │  CATALOG  │         │  SQLite   │         │  Hermes   │     │
│  │  (JSON)   │         │  (file)   │         │  OpenRouter│    │
│  └───────────┘         └───────────┘         │  Telegram │     │
│                                              └───────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Ingest adapters normalize external cost signals → common format
2. Backend stores in SQLite + writes JSONL log
3. Dashboard polls `/api/summary` → renders cost breakdown
4. Effective cost = $0 for self-hosted; Premium equivalent = benchmark cost if paid APIs

---

## Technology Stack

| Layer | Stack |
|-------|-------|
| Runtime | Linux (Ubuntu 22.04+), Docker Compose |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Static HTML5 + Vanilla JS, served by nginx |
| Database | SQLite (file-based, zero-config) |
| Data | JSON pricing catalog + seeded demo data |
| Reverse Proxy | nginx (SPA + API proxy) |
| CI/CD | GitHub Actions (lint, build, test, deploy) |

---

## Features

- ✅ **Pricing catalog**: JSON-backed service pricing (`pricing/catalog.json`)
- ✅ **Ingest adapters**: Hermes, OpenRouter, Telegram (extensible)
- ✅ **Dashboard**: Dark-themed SPA with live 5s polling
- ✅ Cost breakdown: requests, input/output tokens, effective cost, premium equivalent
- ✅ **Demo seeding**: `backend/seed_demo.py` for quick local previews
- ✅ **Dockerized**: Single `docker compose up -d` brings up both services
- ✅ **Health checks**: `/healthz` on backend, nginx serves frontend
- ✅ **Zero-secrets in git**: `.env.example` documents all vars

---

## Services

| Service | Port | Health Endpoint | Purpose |
|---------|------|-----------------|---------|
| **CostForge Backend** | 8000 | `/healthz` | FastAPI - ingest, query, summary |
| **CostForge Frontend** | 8090 | `/` (nginx) | nginx - serves SPA + proxies API |
| **Total** | | | **2 services** |

---

## Getting Started

### Prerequisites
- Docker 24+ & Docker Compose v2
- 2GB+ RAM, 5GB+ disk

### Quick Start

```bash
# 1. Clone
git clone https://github.com/OneByJorah/CostForge.git
cd CostForge

# 2. Verify Docker daemon is running
docker info >/dev/null 2>&1 || echo "Docker daemon is not running"
docker compose version

# 3. Configure (optional - defaults work)
cp .env.example .env  # if exists, else create

# 4. One-command deploy
docker compose up -d

# 5. Verify
curl http://localhost:8090/healthz
```

### Access Points

| Interface | URL |
|-----------|-----|
| **CostForge Dashboard** | http://localhost:8090 |
| **Backend API (dev)** | http://localhost:8000/docs (Swagger) |
| **Backend Health** | http://localhost:8000/healthz |

---

## Environment Variables

All secrets in `.env` (never committed). See `.env.example` for full list.

| Variable | Purpose | Default |
|----------|---------|---------|
| `COSTFORGE_LOG` | Path for JSONL usage log | `/app/usage.jsonl` |
| `PRICING_CATALOG_PATH` | Path to pricing JSON | `/app/pricing/catalog.json` |

---

## Service Management

```bash
# Start all
docker compose up -d

# Stop all
docker compose down

# View logs
docker compose logs -f costforge-backend
docker compose logs -f costforge-frontend

# Restart single service
docker compose restart costforge-backend

# Health check
curl http://localhost:8090/healthz

# Full status
docker compose ps

# Ingest test data
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"source": "test", "model": "test-model", "input_tokens": 1000, "output_tokens": 500}'

# Query summary
curl http://localhost:8000/api/summary?days=7
```

---

## Admin Panel

CostForge uses the **JorahOne AI Stack's Portainer** (port 9000) for container management. For CostForge-specific admin:

- **Backend Swagger UI**: http://localhost:8000/docs
- **nginx config**: `nginx.conf` (API proxy + SPA fallback)
- **Pricing catalog**: `pricing/catalog.json` (edit & reload)

---

## CI/CD & Deployment

**GitHub Actions** (`.github/workflows/ci-cd.yml`):

```yaml
# Triggers: push to main, PR to main
# Jobs:
#   1. lint       - hadolint, shellcheck, yamllint, ruff
#   2. build      - docker compose build
#   3. test       - spin up stack, run healthcheck
#   4. deploy     - SSH to server, pull, restart (on main)
```

**Branch model:** `main` = stable; feature branches for WIP.

**Deploy:** `git push origin main` → auto-deploys via SSH.

---

## Security

- **No secrets in git** - `.env` in `.gitignore`; `.env.example` has placeholders
- **Non-root containers** - Both services run as unprivileged users
- **Read-only mounts** - Config files mounted `:ro`
- **Network isolation** - Services on internal Docker network
- **Input validation** - Pydantic models on all API endpoints

---

## Project Structure

```
CostForge/
├── docker-compose.yml          # 2 services, validated
├── nginx.conf                  # nginx: SPA + API proxy
├── .env.example                # Documented placeholders
├── .env                        # Local secrets (gitignored)
├── .gitignore
├── backend/
│   ├── Dockerfile              # Python 3.12, FastAPI
│   ├── requirements.txt        # fastapi, uvicorn, httpx
│   ├── main.py                 # FastAPI app (100 lines)
│   ├── seed_demo.py            # Demo data seeder
│   └── ingest/
│       ├── hermes_adapter.py
│       ├── openrouter_adapter.py
│       └── telegram_adapter.py
├── frontend/
│   └── dist/
│       └── index.html          # Dark-themed SPA dashboard
├── pricing/
│   └── catalog.json            # Pricing catalog
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # Full CI/CD pipeline
├── docs/
│   └── screenshots/
└── README.md
```

---

## Screenshots

All screenshots are live captures from the local dev instance.

### CostForge Dashboard (Port 8090)
![CostForge Dashboard](docs/screenshots/costforge-dashboard.png)
*Dark-themed SPA: requests, tokens, effective cost, premium equivalent*

### Backend Swagger UI (Port 8000/docs)
![Swagger](docs/screenshots/swagger.png)
*Auto-generated API docs with try-it-out*

---

## License

MIT

---

## Author

Built by **Jhonattan L. Jimenez** (J1admin).

- GitHub: [@OneByJorah](https://github.com/OneByJorah)
- Tailscale: `ollama` (100.92.150.99)