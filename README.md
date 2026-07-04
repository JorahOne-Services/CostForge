# CostForge

> API usage and cost dashboard for free self-hosted versus premium pricing analysis.

![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/status-active-%23FFB300?style=for-the-badge)
![Language](https://img.shields.io/badge/language-Python-informational?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-linux-informational?style=for-the-badge)

CostForge is an enterprise-grade, ops-precise platform built for VIDE and SMB operations. Run it solo. Deliver results.

- ✅ **Pricing catalog**: JSON-backed service pricing (`pricing/catalog.json`)
- ✅ **Ingest adapters**: Hermes, OpenRouter, Telegram (extensible)
- ✅ **Dashboard**: Dark-themed SPA with live 5s polling
- ✅ Cost breakdown: requests, input/output tokens, effective cost, premium equivalent
- ✅ **Demo seeding**: `backend/seed_demo.py` for quick local previews
- ✅ **Dockerized**: Single `docker compose up -d` brings up both services
- ✅ **Health checks**: `/healthz` on backend, nginx serves frontend
- ✅ **Zero-secrets in git**: `.env.example` documents all vars

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
│           

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

## Quickstart

```bash
git clone https://github.com/OneByJorah/CostForge.git
cd CostForge
docker compose up -d
```
Verify at `http://<host-ip>`.

## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| (see Environment Variables) | — | — | — |

For full details, see the in-repo [Environment Variables](#environment-variables) section.

## Roadmap

- Feature parity with production requirements
- Observability and alerting expansions
- Community feedback integration

## License

MIT — Copyright JorahOne, LLC. See [LICENSE](LICENSE) for details.

---

[OneByJorah](https://github.com/OneByJorah) · [JorahOne-Services](https://github.com/JorahOne-Services)
