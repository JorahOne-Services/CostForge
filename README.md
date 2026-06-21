# CostForge (CostForge)

**Version:** v0.1  
**Status:** Active Development  
**Repository:** https://github.com/OneByJorah/CostForge

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Getting Started](#getting-started)
- [Service Management](#service-management)
- [Project Structure](#project-structure)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Overview

Cost calculation and cloud pricing estimation utility built from the J1 NOC Platform UI.

---

## Architecture

Client → Local service (`CostForge`) → data/processing modules → output/api layer.
Secrets and environment configuration are managed via environment files with restrictive permissions.

---

## Technology Stack

|| Layer | Stack |
|---|---|
| Runtime | Linux (Ubuntu 22.04+) |
| Primary Stack | HTML5 / Python / FastAPI |
| VCS | Git + GitHub (`github.com/OneByJorah/CostForge`) |
| Dev Port | Localhost / systemd service |

---

## Features

- Operational dashboard and monitoring (per repo).
- Exportable data / reports where supported.
- Extensible service-based design.
- Dark-themed UI where applicable.

---

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/OneByJorah/CostForge.git
cd CostForge

# 2. Install dependencies
# (see specific subproject docs)

# 3. Start the service
# (see Service Management below)
```

---

## Service Management

```bash
# Start the service (example)
sudo systemctl start CostForge.service
sudo systemctl enable CostForge.service
```

Access the service via your configured localhost port or reverse proxy.

---

## Project Structure

```
CostForge/
├── README.md
├── (additional project files)
```

---

## Screenshots

All screenshots are live captures from the local dev instance.

_(Screenshots will be added after build/run capture.)_

---

## Contributing

1. Create a feature branch off `main`.
2. Follow the existing code style.
3. Submit a PR with description and screenshots for UI changes.

---

## License

MIT

---

## Author

Built by **Jhonattan L. Jimenez**.
