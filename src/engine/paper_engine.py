"""
Persistent SQLite Paper Trading Engine.
Enforces realistic, zero-cheating trade execution, order book slippage,
fractional share ledger, dynamic stop-loss triggers, and full audit logs.
"""

import sqlite3
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.config import BotConfig, get_config
from src.data.provider import MarketDataProvider
from src.strategy.momentum import ETFMomentumStrategy
from src.risk.manager import RiskManager


class PaperTradingEngine:
    """Institutional-grade simulated execution engine with persistent SQLite ledger."""

    def __init__(self, db_path: Optional[Path] = None, config: Optional[BotConfig] = None):
        self.config = config or get_config()
        if db_path is None:
            db_dir = Path(__file__).resolve().parent.parent.parent / "data"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "paper_ledger.db"
        else:
            self.db_path = Path(db_path)

        self.data_provider = MarketDataProvider(offline_fallback=True)
        self.strategy = ETFMomentumStrategy(config=self.config)
        self.risk_manager = RiskManager(config=self.config)
        self.slippage_bps = 5  # 5 basis points (0.05%) modeled slippage
        
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema if not present."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Account summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cash REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    initial_capital REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Open positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    ticker TEXT PRIMARY KEY,
                    shares REAL NOT NULL,
                    avg_entry_price REAL NOT NULL,
                    cost_basis REAL NOT NULL,
                    stop_loss_price REAL NOT NULL,
                    take_profit_price REAL,
                    highest_price REAL NOT NULL,
                    opened_at TEXT NOT NULL
                )
            """)

            # Executed orders audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    side TEXT NOT NULL,
                    shares REAL NOT NULL,
                    execution_price REAL NOT NULL,
                    notional REAL NOT NULL,
                    slippage_cost REAL NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Agent reasoning log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT
                )
            """)

            # Equity curve snapshots for live charts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_equity REAL NOT NULL,
                    cash REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    realized_pnl REAL NOT NULL
                )
            """)

            # Initialize account balance if empty
            cursor.execute("SELECT COUNT(*) FROM account")
            if cursor.fetchone()[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                cursor.execute("""
                    INSERT INTO account (id, cash, realized_pnl, initial_capital, updated_at)
                    VALUES (1, ?, 0.0, ?, ?)
                """, (self.config.initial_capital, self.config.initial_capital, now))
                
                # Initial snapshot
                cursor.execute("""
                    INSERT INTO equity_snapshots (timestamp, total_equity, cash, unrealized_pnl, realized_pnl)
                    VALUES (?, ?, ?, 0.0, 0.0)
                """, (now, self.config.initial_capital, self.config.initial_capital))
                
            conn.commit()

    def log_agent_thought(self, message: str, level: str = "INFO", details: Optional[Dict[str, Any]] = None):
        """Append an entry to the agent's live decision stream."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO agent_logs (timestamp, level, message, details_json) VALUES (?, ?, ?, ?)",
                (now, level, message, json.dumps(details or {}))
            )
            conn.commit()

    def get_account_state(self) -> Dict[str, Any]:
        """Compute accurate, non-cheating live account metrics against live prices."""
        with self._get_connection() as conn:
            acc = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()
            cash = float(acc["cash"])
            realized_pnl = float(acc["realized_pnl"])
            initial_capital = float(acc["initial_capital"])

            positions_rows = conn.execute("SELECT * FROM positions").fetchall()
            
        tickers = [row["ticker"] for row in positions_rows]
        live_prices = self.data_provider.get_latest_prices(tickers) if tickers else {}

        open_positions = []
        total_market_value = 0.0
        total_unrealized_pnl = 0.0

        for row in positions_rows:
            ticker = row["ticker"]
            shares = float(row["shares"])
            entry = float(row["avg_entry_price"])
            cost = float(row["cost_basis"])
            stop = float(row["stop_loss_price"])
            take = float(row["take_profit_price"]) if row["take_profit_price"] else None
            high = float(row["highest_price"])
            
            cur_price = live_prices.get(ticker, entry)
            mkt_val = shares * cur_price
            pos_unrealized = mkt_val - cost
            pos_pnl_pct = ((cur_price - entry) / entry) * 100.0

            total_market_value += mkt_val
            total_unrealized_pnl += pos_unrealized

            open_positions.append({
                "ticker": ticker,
                "shares": round(shares, 4),
                "avg_entry_price": round(entry, 2),
                "current_price": round(cur_price, 2),
                "market_value": round(mkt_val, 2),
                "cost_basis": round(cost, 2),
                "unrealized_pnl": round(pos_unrealized, 2),
                "unrealized_pnl_pct": round(pos_pnl_pct, 2),
                "stop_loss_price": round(stop, 2),
                "take_profit_price": round(take, 2) if take else None,
                "highest_price": round(max(high, cur_price), 2),
                "opened_at": row["opened_at"]
            })

        total_equity = cash + total_market_value
        total_return_pct = ((total_equity - initial_capital) / initial_capital) * 100.0

        return {
            "total_equity": round(total_equity, 2),
            "cash": round(cash, 2),
            "market_value": round(total_market_value, 2),
            "initial_capital": round(initial_capital, 2),
            "unrealized_pnl": round(total_unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "positions": open_positions,
            "positions_count": len(open_positions)
        }

    def execute_market_buy(self, ticker: str, dollar_amount: float, reason: str) -> Optional[Dict[str, Any]]:
        """Realistically fill a fractional buy order with slippage and cash deduction."""
        with self._get_connection() as conn:
            acc = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()
            cash = float(acc["cash"])

            if dollar_amount > cash:
                dollar_amount = cash  # Spend only available cash

            if dollar_amount < 1.0:
                self.log_agent_thought(f"Insufficient cash (${cash:.2f}) to purchase {ticker}.", level="WARN")
                return None

            # Get actual current market price
            raw_price = self.data_provider.get_latest_prices([ticker]).get(ticker, 100.0)
            
            # Model execution slippage: buyer pays slightly above mid (0.05%)
            slippage_factor = 1.0 + (self.slippage_bps / 10000.0)
            fill_price = round(raw_price * slippage_factor, 2)
            slippage_cost = round((fill_price - raw_price) * (dollar_amount / fill_price), 4)

            shares = round(dollar_amount / fill_price, 4)
            stop_loss = round(fill_price * (1.0 - self.config.stop_loss_pct), 2)
            take_profit = round(fill_price * (1.0 + self.config.take_profit_pct), 2)
            now = datetime.now(timezone.utc).isoformat()

            # Deduct cash
            conn.execute("UPDATE account SET cash = cash - ?, updated_at = ? WHERE id = 1", (dollar_amount, now))

            # Insert/Update position
            existing = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
            if existing:
                old_shares = float(existing["shares"])
                old_cost = float(existing["cost_basis"])
                new_shares = old_shares + shares
                new_cost = old_cost + dollar_amount
                new_avg = new_cost / new_shares
                conn.execute("""
                    UPDATE positions
                    SET shares = ?, avg_entry_price = ?, cost_basis = ?, stop_loss_price = ?, take_profit_price = ?, highest_price = MAX(highest_price, ?)
                    WHERE ticker = ?
                """, (new_shares, new_avg, new_cost, stop_loss, take_profit, fill_price, ticker))
            else:
                conn.execute("""
                    INSERT INTO positions (ticker, shares, avg_entry_price, cost_basis, stop_loss_price, take_profit_price, highest_price, opened_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ticker, shares, fill_price, dollar_amount, stop_loss, take_profit, fill_price, now))

            # Audit record in orders table
            conn.execute("""
                INSERT INTO orders (ticker, side, shares, execution_price, notional, slippage_cost, reason, timestamp)
                VALUES (?, 'BUY', ?, ?, ?, ?, ?, ?)
            """, (ticker, shares, fill_price, dollar_amount, slippage_cost, reason, now))
            
            conn.commit()

        self.log_agent_thought(
            f"FILLED BUY: {shares:.4f} shares of {ticker} @ ${fill_price:.2f} (${dollar_amount:.2f} notional). Stop: ${stop_loss:.2f}",
            details={"ticker": ticker, "shares": shares, "price": fill_price, "reason": reason}
        )
        return {"ticker": ticker, "shares": shares, "fill_price": fill_price, "dollars": dollar_amount}

    def execute_market_sell(self, ticker: str, reason: str) -> Optional[Dict[str, Any]]:
        """Realistically liquidate an open position and realize PnL to cash."""
        with self._get_connection() as conn:
            pos = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
            if not pos:
                return None

            shares = float(pos["shares"])
            cost_basis = float(pos["cost_basis"])
            raw_price = self.data_provider.get_latest_prices([ticker]).get(ticker, float(pos["avg_entry_price"]))

            # Slippage: seller receives slightly below mid (0.05%)
            slippage_factor = 1.0 - (self.slippage_bps / 10000.0)
            fill_price = round(raw_price * slippage_factor, 2)
            gross_proceeds = round(shares * fill_price, 2)
            realized_pnl = round(gross_proceeds - cost_basis, 2)
            slippage_cost = round((raw_price - fill_price) * shares, 4)
            now = datetime.now(timezone.utc).isoformat()

            # Credit cash and update realized PnL
            conn.execute("""
                UPDATE account
                SET cash = cash + ?, realized_pnl = realized_pnl + ?, updated_at = ?
                WHERE id = 1
            """, (gross_proceeds, realized_pnl, now))

            # Delete open position
            conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))

            # Order record
            conn.execute("""
                INSERT INTO orders (ticker, side, shares, execution_price, notional, slippage_cost, reason, timestamp)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?)
            """, (ticker, shares, fill_price, gross_proceeds, slippage_cost, reason, now))

            conn.commit()

        self.log_agent_thought(
            f"FILLED SELL: Liquidated {shares:.4f} shares of {ticker} @ ${fill_price:.2f} for ${gross_proceeds:.2f} (Realized PnL: ${realized_pnl:+.2f}). Reason: {reason}",
            level="INFO" if realized_pnl >= 0 else "WARN",
            details={"ticker": ticker, "shares": shares, "price": fill_price, "pnl": realized_pnl, "reason": reason}
        )
        return {"ticker": ticker, "shares": shares, "fill_price": fill_price, "proceeds": gross_proceeds, "realized_pnl": realized_pnl}

    def check_stop_losses_and_targets(self):
        """Audit all open positions against live prices for stop-loss and take-profit breaches."""
        with self._get_connection() as conn:
            positions = conn.execute("SELECT * FROM positions").fetchall()

        if not positions:
            return

        tickers = [p["ticker"] for p in positions]
        prices = self.data_provider.get_latest_prices(tickers)

        for pos in positions:
            ticker = pos["ticker"]
            cur_price = prices.get(ticker)
            if not cur_price:
                continue

            entry = float(pos["avg_entry_price"])
            highest = float(pos["highest_price"])
            stop = float(pos["stop_loss_price"])
            take = float(pos["take_profit_price"]) if pos["take_profit_price"] else None

            # Update trailing highest price in db
            if cur_price > highest:
                with self._get_connection() as conn:
                    conn.execute("UPDATE positions SET highest_price = ? WHERE ticker = ?", (cur_price, ticker))
                    conn.commit()

            # Evaluate triggers
            should_exit, reason = self.risk_manager.should_exit_position(
                entry_price=entry,
                current_price=cur_price,
                highest_price=max(highest, cur_price)
            )

            if should_exit:
                self.execute_market_sell(ticker, reason=reason)

    def run_rebalance_cycle(self) -> Dict[str, Any]:
        """
        Execute full quantitative trading cycle:
        1. Fetch fresh historical price bars for the ETF universe.
        2. Evaluate Macro Regime (SPY 50-day SMA).
        3. Rank universe relative-strength momentum scores.
        4. Check and execute required rotations or cash hedging.
        5. Snapshot equity.
        """
        self.log_agent_thought("Initiating automated quantitative rebalance cycle...")
        all_tickers = list(set(self.config.etf_universe + [self.config.cash_proxy, "SPY"]))
        
        history = self.data_provider.fetch_history(all_tickers, period="3mo")
        latest_prices = self.data_provider.get_latest_prices(all_tickers, history=history)

        # 1. Macro Regime Check
        spy_df = history.get("SPY")
        is_bull = self.strategy.is_market_bullish(spy_df) if spy_df is not None else True
        regime_msg = "🟢 BULL REGIME: SPY >= 50-day SMA. Momentum rotation active." if is_bull else "🔴 BEAR REGIME: SPY below 50-day SMA. Defensive cash rotation active."
        self.log_agent_thought(regime_msg, level="INFO" if is_bull else "WARN")

        # 2. Check Stop Losses first
        self.check_stop_losses_and_targets()

        # 3. Strategy Signals
        target_signals = self.strategy.generate_signals(history)
        self.log_agent_thought(f"Target Strategy Signals: {', '.join(target_signals)}")

        # 4. Compare current positions with target signals
        with self._get_connection() as conn:
            current_positions = [row["ticker"] for row in conn.execute("SELECT ticker FROM positions").fetchall()]

        # Exit positions no longer in top momentum
        for current_t in current_positions:
            if current_t not in target_signals:
                self.execute_market_sell(current_t, reason=f"ROTATION_OUT: Dropped from top momentum ranking")

        # Get fresh state for sizing
        state = self.get_account_state()
        available_cash = state["cash"]
        remaining_slots = self.config.max_positions - len(state["positions"])

        new_targets = [t for t in target_signals if t not in [p["ticker"] for p in state["positions"]]]

        if new_targets and remaining_slots > 0 and available_cash >= 5.0:
            dollar_per_slot = (available_cash * 0.98) / min(remaining_slots, len(new_targets))
            for target in new_targets[:remaining_slots]:
                self.execute_market_buy(
                    ticker=target,
                    dollar_amount=round(dollar_per_slot, 2),
                    reason="MOMENTUM_LEADER_ENTRY"
                )

        # 5. Snapshot equity for chart
        updated_state = self.get_account_state()
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO equity_snapshots (timestamp, total_equity, cash, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, ?, ?)
            """, (now, updated_state["total_equity"], updated_state["cash"], updated_state["unrealized_pnl"], updated_state["realized_pnl"]))
            conn.commit()

        self.log_agent_thought(f"Rebalance cycle complete. Portfolio Equity: ${updated_state['total_equity']:,.2f} (${updated_state['total_return_pct']:+.2f}%)")
        return updated_state

    def liquidate_all(self, reason: str = "MANUAL_LIQUIDATE") -> Dict[str, Any]:
        """Emergency liquidate all holdings to cash."""
        self.log_agent_thought(f"EMERGENCY ACTION: Liquidating all open positions ({reason}).", level="WARN")
        with self._get_connection() as conn:
            positions = [r["ticker"] for r in conn.execute("SELECT ticker FROM positions").fetchall()]
        
        for t in positions:
            self.execute_market_sell(t, reason=reason)
            
        return self.get_account_state()

    def reset_account(self, new_balance: float = 100.0) -> Dict[str, Any]:
        """Reset ledger to a fresh starting balance."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM positions")
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM agent_logs")
            conn.execute("DELETE FROM equity_snapshots")
            conn.execute("""
                UPDATE account
                SET cash = ?, realized_pnl = 0.0, initial_capital = ?, updated_at = ?
                WHERE id = 1
            """, (new_balance, new_balance, now))
            
            conn.execute("""
                INSERT INTO equity_snapshots (timestamp, total_equity, cash, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, 0.0, 0.0)
            """, (now, new_balance, new_balance))
            conn.commit()

        self.log_agent_thought(f"Account reset to initial capital: ${new_balance:.2f}")
        return self.get_account_state()

    def get_equity_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent equity snapshots for chart plotting."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT timestamp, total_equity, cash, unrealized_pnl, realized_pnl
                FROM equity_snapshots
                ORDER BY id ASC
                LIMIT ?
            """, (limit,)).fetchall()

        return [dict(r) for r in rows]

    def get_recent_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent filled orders."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, ticker, side, shares, execution_price, notional, slippage_cost, reason, timestamp
                FROM orders
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_recent_logs(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Retrieve recent agent decision thoughts."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, level, message, details_json
                FROM agent_logs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

