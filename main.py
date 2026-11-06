#!/usr/bin/env python3
"""
ETF-t Trading Bot CLI Runner.
Orchestrates data ingestion, momentum ranking, risk-bounded allocation,
and fractional order execution.
"""

import sys
import argparse
from pathlib import Path

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import get_config
from src.data.provider import MarketDataProvider
from src.strategy.momentum import ETFMomentumStrategy
from src.risk.manager import RiskManager
from src.execution.alpaca import AlpacaBroker


def run_bot(dry_run: bool = True):
    print("=" * 65)
    print("        🚀 ETF-t: QUANTITATIVE ETF MOMENTUM ENGINE")
    print("=" * 65)

    config = get_config()
    print(f"[*] Universe:           {', '.join(config.etf_universe)}")
    print(f"[*] Cash Proxy:         {config.cash_proxy}")
    print(f"[*] Max Positions:      {config.max_positions}")
    print(f"[*] Stop-Loss / Target: {config.stop_loss_pct*100:.1f}% / {config.take_profit_pct*100:.1f}%")
    print(f"[*] Execution Mode:     {'DRY RUN (Simulation)' if dry_run else 'LIVE/PAPER EXECUTION'}")
    print("-" * 65)

    # 1. Initialize Components
    data_provider = MarketDataProvider(offline_fallback=True)
    strategy = ETFMomentumStrategy(config=config, lookback_days=20, trend_filter_days=50)
    risk_manager = RiskManager(config=config, cash_buffer_pct=0.02)
    broker = AlpacaBroker(config=config)

    # 2. Portfolio Balance Check
    equity = broker.get_portfolio_equity()
    print(f"[*] Current Portfolio Equity: ${equity:,.2f}")

    # 3. Market Data Ingestion
    print("[*] Fetching historical price data...")
    all_tickers = list(set(config.etf_universe + [config.cash_proxy, "SPY"]))
    history = data_provider.fetch_history(all_tickers, period="3mo")
    latest_prices = data_provider.get_latest_prices(all_tickers, history=history)

    # 4. Strategy & Regime Evaluation
    spy_df = history.get("SPY")
    is_bull = strategy.is_market_bullish(spy_df) if spy_df is not None else True
    print(f"[*] Macro Regime:       {'🟢 BULL MARKET (SPY >= 50-day SMA)' if is_bull else '🔴 BEAR / CORRECTION (Defensive Cash Allocation)'}")

    # Display Momentum Scores
    print("\n--- Universe Relative Strength Momentum (20-Day Lookback) ---")
    for t in config.etf_universe:
        score = strategy.calculate_momentum_score(history.get(t)) if t in history else -999.0
        price = latest_prices.get(t, 0.0)
        score_str = f"{score*100:+.2f}%" if score > -900 else "N/A"
        print(f"  • {t:5} : Price ${price:7.2f} | 20d Return: {score_str}")

    target_tickers = strategy.generate_signals(history)
    print(f"\n[*] Strategy Target Signal: {target_tickers}")

    # 5. Risk Management & Position Sizing
    allocations = risk_manager.calculate_allocations(
        total_equity=equity,
        selected_tickers=target_tickers,
        current_prices=latest_prices
    )

    print("\n--- Target Rebalancing Allocations ($100 Micro-Sizing) ---")
    print(f"{'Ticker':<8}{'Target $':<12}{'Shares':<12}{'Price':<10}{'Stop Loss':<12}{'Take Profit':<12}")
    print("-" * 65)
    for alloc in allocations:
        tp_str = f"${alloc.take_profit_price:.2f}" if alloc.take_profit_price else "None"
        print(f"{alloc.ticker:<8}${alloc.target_dollars:<11.2f}{alloc.target_shares:<12.4f}${alloc.current_price:<9.2f}${alloc.stop_loss_price:<11.2f}{tp_str:<12}")

    # 6. Execution Layer
    print("\n--- Order Execution Summary ---")
    for alloc in allocations:
        if dry_run:
            print(f"  [SIMULATED] BUY ${alloc.target_dollars:.2f} of {alloc.ticker} (~{alloc.target_shares:.4f} shares) @ ~${alloc.current_price:.2f}")
        else:
            result = broker.place_dollar_order(
                ticker=alloc.ticker,
                dollar_amount=alloc.target_dollars,
                side="buy"
            )
            print(f"  [{result.get('status', 'OK')}] {result.get('side')} {alloc.ticker}: {result.get('notional')}")

    print("\n" + "=" * 65)
    print("  ✅ Rebalance Cycle Complete.")
    print("=" * 65)


def show_status():
    config = get_config()
    broker = AlpacaBroker(config=config)
    print("=" * 50)
    print("       📊 ETF-t PORTFOLIO STATUS")
    print("=" * 50)
    print(f"Broker Connected: {broker.is_connected} ({'Paper' if config.alpaca_paper else 'Live'})")
    print(f"Total Equity:     ${broker.get_portfolio_equity():,.2f}")
    positions = broker.get_open_positions()
    print("\nOpen Positions:")
    if not positions:
        print("  (No open positions)")
    else:
        for ticker, qty in positions.items():
            print(f"  • {ticker:6} : {qty:.4f} shares")
    print("=" * 50)


def run_web(host: str = "127.0.0.1", port: int = 8000):
    """Launch FastAPI live paper-trading web dashboard."""
    import uvicorn
    print("=" * 65)
    print("  🌐 ETF-t LIVE AGENTIC TRADING COCKPIT")
    print("=" * 65)
    print(f"[*] Serving web dashboard at: http://{host}:{port}")
    print(f"[*] Open this URL in your browser to view live simulated trading.")
    print("=" * 65)
    uvicorn.run("src.api.server:app", host=host, port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="ETF-t: Quantitative ETF Momentum Trading Bot")
    parser.add_argument("--web", action="store_true", default=False, help="Launch live web dashboard (FastAPI + WebSockets)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind web dashboard (default 8000)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run simulation without placing broker orders")
    parser.add_argument("--execute", action="store_true", default=False, help="Submit orders to Alpaca broker")
    parser.add_argument("--status", action="store_true", help="Display current account balance and open positions")

    args = parser.parse_args()

    if args.web:
        run_web(port=args.port)
    elif args.status:
        show_status()
    elif args.execute:
        run_bot(dry_run=False)
    else:
        # Default to safe dry-run simulation
        run_bot(dry_run=True)


if __name__ == "__main__":
    main()

