# INTENT.md — J1-PIPELINE Phase -1 (ORACLE)

**Repository:** `OneByJorah/CostForge`
**Analysis Date:** 2026-07-05
**Analyst:** J1-PIPELINE ORACLE (read-only)
**Status:** Intent Reconstructed

---

## What This System Does

### Technical Role

CostForge is a **self-hosted API cost estimation and metering dashboard** that operates as a transparent HTTP reverse proxy. It sits between client applications and LLM/API providers, intercepting every request to:

1. **Proxy traffic** to configured providers — local (Ollama, LM Studio, vLLM, Headroom) and cloud-free (Groq, OpenRouter free models, Gemini free tier, HuggingFace Inference)
2. **Meter token usage** by parsing provider-specific response formats (OpenAI-compatible, Ollama, generic)
3. **Estimate costs** by mapping each local/free model to a premium API equivalent (e.g., `llama3.1:8b` → `gpt-4o-mini`) and computing what the request *would have cost* on paid APIs
4. **Store usage data** in SQLite with WAL mode, indexed by timestamp and source
5. **Serve a live dark-themed SPA dashboard** with real-time WebSocket updates, provider breakdowns, time-series sparklines, and cost comparison visuals
6. **Accept direct ingestion** from external adapters (Hermes Agent, GitHub API, Telegram bot, OpenRouter) via a POST `/ingest` endpoint
7. **Provide a WebSocket live feed** (`/ws`) that pushes new usage records to all connected dashboard clients in real time

### Operational Role

CostForge is the **cost observability layer** for the JorahOne AI infrastructure. It answers the question: *"How much money am I saving by running local models or using free-tier APIs instead of paying for premium cloud APIs?"* It runs as a Docker Compose stack (FastAPI backend + nginx frontend) with health checks, healthz endpoint, and automatic restart.

### Architecture

```
Browser ──▶ Nginx (port 8090) ──▶ FastAPI Backend (port 8000)
                                       │
                              ┌────────┴────────┐
                              ▼                  ▼
                         SQLite (usage)    JSON (pricing catalog)
                              │
                              ▼
                    WebSocket live feed (/ws)
```

### Key Components

| Component | Technology | Role |
|-----------|-----------|------|
| Backend | FastAPI + uvicorn | Proxy, metering, API, WebSocket hub |
| Database | SQLite (WAL) | Usage records, event log |
| Frontend | Vanilla HTML/CSS/JS SPA | Dark dashboard, live updates |
| Proxy | nginx | Reverse proxy, static file serving |
| Pricing | JSON catalog | Per-million-token rates for premium models |
| Providers | JSON config | Provider definitions with response format + premium mappings |
| Adapters | Python modules | Hermes, GitHub, Telegram, OpenRouter ingestion |

---

## Why This Was Built

### Real Problem

Developers and teams running local LLMs (Ollama, LM Studio, vLLM) or using free-tier cloud APIs (Groq, OpenRouter free models, Gemini free tier, HuggingFace Inference) have **no visibility** into the economic value of their infrastructure choices. The costs are effectively zero on the bill, but the usage volume, token counts, and equivalent commercial value are invisible. Without this data, it's impossible to:

- Justify GPU hardware expenditure for local inference
- Make informed build-vs-buy decisions between local and cloud models
- Track aggregate usage across a heterogeneous provider landscape
- Provide cost transparency to stakeholders

### Why Existing Tools Were Insufficient

| Tool | Gap |
|------|-----|
| Cloud provider dashboards (OpenAI, Anthropic, Google) | Only show what you *actually paid* — nothing for local/free usage |
| OpenRouter billing | Only tracks paid usage through their platform |
| Ollama logs | Raw text logs, no aggregation, no cost comparison |
| Prometheus/Grafana | General-purpose monitoring, no LLM-specific cost semantics |
| Spreadsheet tracking | Manual, error-prone, doesn't capture real-time proxy traffic |

No existing tool provided a **zero-configuration proxy that automatically meters every LLM API call, maps local models to premium equivalents, and shows the savings in real time** — all self-hosted with zero external dependencies.

### What Triggered Development

The JorahOne ecosystem runs multiple local LLM providers (Ollama, vLLM, Headroom context optimizer) alongside cloud free tiers. The team needed to:

- Justify the capital expenditure on GPU hardware for local inference
- Compare local model quality/cost trade-offs against premium APIs
- Track aggregate usage across all providers from a single pane of glass
- Provide cost transparency to stakeholders without exposing API keys or cloud billing portals

The initial commit (`5fa1e7c` — "chore: initial CostForge scaffold with FastAPI backend + dashboard") established the core proxy + dashboard pattern from day one. CostForge was built to answer these questions with a single `docker compose up`.

### Ecosystem Fit

CostForge is the **cost observability pillar** of the JorahOne infrastructure stack. It integrates with:

- **Hermes Agent** — adapter normalizes Hermes usage events for cost tracking
- **GitHub API** — adapter meters GitHub API call volume (issues, repos, workflows)
- **Telegram bot** — adapter meters Telegram message processing
- **OpenRouter** — adapter tracks OpenRouter model usage
- **Headroom** — native provider support for the JorahOne context optimization proxy (from `StackDeploy/vendor/headroom`)
- **StackDeploy** — referenced in `stack_manifest.json` as a deployable service

It is designed to be the single source of truth for "what is our AI infrastructure actually costing us, and what would it cost if we switched to premium APIs?"

---

## Operational Classification

**Classification: PRODUCTION**

Evidence:

| Criterion | Status |
|-----------|--------|
| Docker Compose deployment | ✅ `docker-compose.yml` with health checks, restart policy, persistent volume |
| Health check endpoint | ✅ `/healthz` + shell healthcheck script (`scripts/healthcheck.sh`) |
| CI/CD | ✅ CodeQL analysis on push/PR/schedule (`.github/workflows/codeql.yml`) |
| Dependency management | ✅ Dependabot for pip, npm, Docker, GitHub Actions (`.github/dependabot.yml`) |
| Security policy | ✅ `SECURITY.md` with disclosure process and 90-day timeline |
| Code of Conduct | ✅ `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1) |
| Contributing guide | ✅ `CONTRIBUTING.md` with issue/PR labels |
| MIT License | ✅ `LICENSE` |
| Persistent storage | ✅ SQLite with WAL mode, Docker volume (`costforge-data`) |
| Graceful degradation | ✅ Proxy errors return 502 with diagnostic message |
| Non-root container | ✅ `USER costforge` in Dockerfile (UID 1000) |
| CORS configured | ✅ Wide-open CORS for proxy flexibility |
| Security audits in git history | ✅ Two commits: `401570c` (redact exposed Tailscale IPs) and `d2071d4` (sanitize email references) |
| Issue/PR templates | ✅ Bug report + feature request + PR template in `.github/` |
| Dashboard screenshots | ✅ Live screenshots in `docs/screenshots/` |

---

## Key Architectural Decisions

1. **Proxy-based metering over agent-side instrumentation** — Rather than modifying every client application to report usage, CostForge intercepts traffic at the proxy layer. Clients just change their base URL. This is the single most important design decision — it makes adoption zero-friction.

2. **SQLite over PostgreSQL** — Zero external dependencies. The data volume (token usage records) is modest enough that SQLite with WAL mode handles it comfortably. No separate database server to manage.

3. **Premium equivalence mapping** — Rather than trying to compute "real" costs for free/local models (which are $0 or sunk hardware cost), CostForge shows what the same usage *would have cost* on comparable premium APIs. This measures opportunity cost, not actual spend — the key insight that makes the tool valuable.

4. **Response format parsers** — Three parsers (OpenAI, Ollama, generic) handle the major LLM API formats. The generic parser falls back to token estimation from text length when the response doesn't include a usage field. This enables broad provider coverage without per-provider integration work.

5. **WebSocket live feed** — The `LiveHub` class broadcasts new usage records to all connected dashboard clients in real time, making the dashboard feel alive without polling. The dashboard reconnects automatically on disconnect.

6. **Adapters for external ingestion** — The `/ingest` endpoint and adapter modules allow non-proxied services (Hermes, GitHub, Telegram) to push usage data into CostForge, making it a universal cost aggregator beyond just proxied traffic.

7. **Single-file SPA frontend** — The entire dashboard is a single `index.html` with inline CSS and JavaScript. No build step, no npm, no framework. This keeps deployment trivial and eliminates frontend dependencies.

---

## Repository Structure

```
CostForge/
├── backend/
│   ├── main.py              # FastAPI app: proxy, API, WebSocket, DB (566 lines)
│   ├── providers.json       # Provider definitions (Ollama, Groq, etc.)
│   ├── pricing.json         # Premium API pricing catalog (duplicate of pricing/catalog.json)
│   ├── seed_demo.py         # Demo data seeder (5 sample events)
│   ├── Dockerfile           # Python 3.12-slim, non-root user
│   ├── requirements.txt     # fastapi, uvicorn, httpx
│   └── ingest/
│       ├── __init__.py      # Empty
│       ├── hermes_adapter.py      # Hermes Agent usage adapter
│       ├── github_adapter.py      # GitHub API usage adapter
│       ├── telegram_adapter.py    # Telegram bot usage adapter
│       └── openrouter_adapter.py  # OpenRouter usage adapter
├── frontend/
│   └── dist/
│       └── index.html       # SPA dashboard (vanilla JS, inline CSS, 259 lines)
├── pricing/
│   └── catalog.json         # Full pricing catalog (same as backend/pricing.json)
├── scripts/
│   └── healthcheck.sh       # Shell health check script
├── docs/
│   └── screenshots/         # Dashboard screenshots (2 PNGs)
├── .github/
│   ├── workflows/codeql.yml # CodeQL security analysis
│   ├── dependabot.yml       # Automated dependency updates
│   └── ISSUE_TEMPLATE/      # Bug report + feature request templates
├── docker-compose.yml       # Multi-service deployment (backend + nginx frontend)
├── nginx.conf               # Reverse proxy config
├── stack_manifest.json      # Stack metadata
├── review_findings.json     # Audit findings (2 items: Docker daemon not running)
├── deploy_log.txt           # Deployment attempt log
├── INTENT.md                # This file
├── README.md                # Project documentation
├── SECURITY.md              # Security policy
├── CONTRIBUTING.md          # Contribution guide
├── CODE_OF_CONDUCT.md       # Code of conduct
├── LICENSE                  # MIT License
└── .gitignore               # Python/Docker/IDE ignores
```

---

## Notes

### Config-Drift Findings

1. **Dependabot npm ecosystem mismatch** — `.github/dependabot.yml` configures an `npm` ecosystem, but no `package.json` exists anywhere in the repo. The frontend is a single-file SPA with no npm dependencies. This is a template vestige from the J1 repo template — the npm entry should be removed.

2. **Duplicate pricing files** — `backend/pricing.json` and `pricing/catalog.json` contain identical data. The backend loads `pricing/catalog.json` at import time (line 32 of `main.py`), while `backend/pricing.json` appears unused by the running application. One should be removed or symlinked.

3. **Empty `docs/` directory** — The `docs/` directory contains only screenshots. No setup documentation, troubleshooting guides, or integration docs exist beyond the README. This is a documentation gap.

4. **Empty `__init__.py`** — `backend/ingest/__init__.py` is empty. The adapter modules are imported directly by external consumers, not through the package. This is harmless but worth noting.

5. **Deploy blocker documented** — `review_findings.json` and `deploy_log.txt` document that Docker daemon is not running on the analysis host. The README does not explicitly state that Docker must be running before `docker compose up -d`.

### Git History Highlights

- **Initial commit** (`5fa1e7c`): "chore: initial CostForge scaffold with FastAPI backend + dashboard" — the core proxy + dashboard pattern was the first thing built
- **Security audits**: Two security-related commits — `401570c` (redact exposed Tailscale IPs) and `d2071d4` (sanitize email references) — indicating active security posture maintenance
- **Dependency bumps**: Multiple Dependabot-style commits updating uvicorn, fastapi, actions/checkout, and codeql-action
- **Ruff auto-fix**: `12146ed` applied ruff auto-fixes and portfolio standardization
- **Headroom provider**: `0d4f76c` added the Headroom context optimization proxy as a provider

### Classification Evidence Summary

CostForge qualifies as **Production** based on: Docker Compose deployment with health checks, CI/CD (CodeQL), Dependabot, security policy, CoC, contributing guide, MIT license, persistent storage, non-root container, graceful degradation, security audit history, and issue/PR templates. The only gap is the missing Docker daemon prerequisite documentation in the README.
