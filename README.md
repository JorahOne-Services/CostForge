# CostForge

Self-hosted cloud and API cost estimation dashboard — track, compare, and estimate cloud/LLM API usage costs with zero external dependencies.

![status](https://img.shields.io/badge/status-active-FFB300?style=flat-square)
![language](https://img.shields.io/badge/python-3.10+-0d0d0c?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-FFB300?style=flat-square)

## Overview

CostForge is a self-hosted cost estimation dashboard for cloud infrastructure and LLM API usage. It aggregates pricing across AWS, GCP, Azure, OpenAI, Anthropic, and more, with a production-ready dark-themed dashboard, local SQLite storage, and Docker Compose deployment. Zero external dependencies, zero secrets in git.

## Features

- Multi-provider aggregation — compare pricing across AWS, GCP, Azure, OpenAI, Anthropic, and more
- 100% self-hosted — zero external dependencies, zero secrets in git
- Dark dashboard — production-ready dark-themed single-page dashboard
- Local storage — SQLite for usage data, JSON for pricing catalogs
- Cost comparison — compare self-hosted vs premium API pricing
- Real-time cost tracking with historical charts
- FastAPI backend with REST API
- Docker Compose deployment with Nginx reverse proxy

## Architecture / Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **Frontend**: Vanilla JS (dark theme dashboard)
- **Reverse Proxy**: Nginx
- **Deployment**: Docker Compose

## Installation

```bash
git clone https://github.com/OneByJorah/CostForge.git
cd CostForge

cp .env.example .env  # Configure providers
docker compose up -d
```

Open `http://localhost:3000` for the dashboard.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | List all providers |
| `/api/costs` | GET | Get cost data |
| `/api/compare` | POST | Compare pricing |

## License

MIT — see [LICENSE](LICENSE).

---
Part of the JorahOne / J1 ecosystem — cost visibility for self-hosted AI infrastructure.
