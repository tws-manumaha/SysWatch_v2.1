# SysWatch v2.1

Advanced AI-powered IT infrastructure monitoring platform.

## What's New in v2.1

- **Real connection pooling** (DBUtils PooledDB) — no more per-query connections
- **Database-backed brute-force protection** — survives restarts
- **JWT authentication** with refresh tokens + API key support
- **AES-256-GCM encryption** for all stored credentials
- **No stubs** — every endpoint does real work
- **Advanced AI module** — predictive analytics, human-in-the-loop remediation
- **Real alert engine** — rules evaluated against live metrics
- **Cross-OS agent** — Python agent for Linux, Windows, macOS
- **Let's Encrypt SSL** integration
- **OS-independent** deployment (Docker, bare metal, WSL)

## Architecture

```
backend/
  app.py              — Flask app entry (Gunicorn-ready)
  schema.sql           — Complete MySQL 8.0 schema
  requirements.txt
  modules/
    config.py          — Centralized config (.env support)
    database.py         — Connection pooling, transactions
    logging_manager.py  — File + DB logging (timezone-aware)
    security.py         — Auth, encryption, brute-force, validation
    scheduler.py        — APScheduler with Redis locking
    backup_manager.py   — Real backups with stable IDs
    alert_engine.py     — Rule evaluation engine
    host_checker.py     — Host status monitoring
    ai/
      llm.py            — Multi-provider fallback chain
      log_intelligence.py — Statistical anomaly detection
      assistant.py      — AI remediation with human-in-the-loop
    api_*.py            — 17 API blueprints
agents/
  syswatch_agent.py    — Cross-OS monitoring agent
```

## Quick Start

```bash
# Docker
docker-compose up -d

# Bare metal
sudo ./install.sh
```

See [INSTALL.md](INSTALL.md) for detailed instructions.

## License

MIT
