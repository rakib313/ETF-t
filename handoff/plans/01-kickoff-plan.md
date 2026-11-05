# Epoch 01: Kickoff Plan & Core Scaffolding

## Chronicles & Context
- **Origin:** Project initialized on 2026-11-06 in `/home/whoami/util/GitRepo/ETF-t`.
- **Scope:** Architecture scaffolding, risk manager, momentum strategy module, fractional broker abstraction, and unit test suite.
- **Budget Calibration:** Calibrated specifically for micro-starting capital ($100 starting budget with fractional share support).

## Technical Specification
1. **Repository & Tooling Baseline:**
   - Git repository initialized on `main` branch.
   - Projected 21 agentic skills from vault profile `etf-trading` via relative symlinks into `.agents/skills/`.
   - `.gitignore`, `.env.example`, `pyproject.toml`, and `requirements.txt` configured.
2. **Core Modules Implemented:**
   - `src/config.py`: Validated Pydantic configuration with risk limits and broker switches.
   - `src/risk/manager.py`: Position sizing engine computing fractional allocations, 2% cash buffer, 5% stop-loss, and 10% take-profit.
   - `src/strategy/momentum.py`: Dual-momentum engine with SPY 50-day SMA regime filter and cash proxy hedging.
   - `src/execution/alpaca.py`: Broker interface with fractional notional order placement and offline simulation mode.
3. **Verification Checklist:**
   - [x] Scaffolding tests for Config validation (`tests/test_config.py`).
   - [x] Unit tests for Risk Engine with $100 equity (`tests/test_risk.py`).
   - [x] Unit tests for Momentum Strategy & Bear Market Cash Hedging (`tests/test_strategy.py`).
