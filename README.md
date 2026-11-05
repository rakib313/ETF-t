# ETF-t: Algorithmic ETF Trading Bot

Automated quantitative ETF trading engine tailored for systematic momentum rotation, mean-reversion, and strict capital preservation. Built for micro-to-standard accounts (supporting fractional shares from \$100 onward).

## Key Pillars
- **Zero Idiosyncratic Risk:** Traded strictly on liquid ETFs (`SPY`, `QQQ`, `XLK`, `XLF`, `XLE`, `GLD`, `TLT`).
- **Institutional Risk Filter:** Hard stop-losses, maximum drawdown triggers, and automated rotation into cash proxies (`BIL`/`SGOV`) during bear regimes.
- **Fractional Sizing:** Optimized for Alpaca Paper & Live API, allowing granular dollar-weighted allocation with as little as \$100.
- **Test-Driven:** 100% test coverage on order generation, signal filtering, and position sizing.

## Quickstart

```bash
# 1. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env with your Alpaca paper API keys

# 4. Run test suite
pytest
```

## Directory Structure
```
ETF-t/
├── handoff/             # Handoff lifecycle cockpit (Epoch tracking & ADRs)
├── src/
│   ├── config.py        # Settings & environment variables (Pydantic)
│   ├── data/            # Market data feeds & caching (Alpaca / yfinance)
│   ├── strategy/        # Signal generation & momentum ranking
│   ├── risk/            # Position sizing & circuit breakers ($100 budget)
│   └── execution/       # Broker routing & fractional order placement
└── tests/               # Unit and regression test suite
```

