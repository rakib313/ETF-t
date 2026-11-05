---
title: "ETF-t"
type: project
status: active
created: 2026-11-06
source_repo: "/home/whoami/util/GitRepo/ETF-t"
---
# ETF-t: Algorithmic ETF Trading Bot

Systematic ETF momentum rotation and swing trading engine designed for capital preservation, automated risk limits, and micro-to-standard accounts ($100+ starting capital).

## Key Components
- **Config & Settings (`src/config.py`):** Pydantic v2 settings, Alpaca API credentials, risk thresholds.
- **Risk Engine (`src/risk/manager.py`):** Dollar-allocation per position, fractional sizing (4 decimals), trailing stops, and cash buffering.
- **Strategy Engine (`src/strategy/momentum.py`):** Relative-strength ranking with absolute macro regime trend filter (SPY vs SMA) and auto-cash hedging (`BIL`).
- **Broker Interface (`src/execution/alpaca.py`):** Alpaca Paper & Live Trading API client with fractional notional order routing and simulated fallback.

## Folders and files
- handoff/
- src/
- tests/
- README.md
- pyproject.toml
- requirements.txt
- .env.example
