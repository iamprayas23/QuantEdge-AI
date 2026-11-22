# QuantEdge

**Institutional-Grade Quantitative Backtesting, Regime Analysis & Grounded AI Platform**

QuantEdge is a full-stack quantitative research, deterministic backtesting, and AI-assisted strategy engineering platform designed for hedge funds, prop desks, and systematic traders.

---

## Architecture Overview

```
quantedge/
├── api_platform/              # FastAPI Application Layer
│   ├── auth/                  # JWT auth, user/workspace ownership, hashing
│   ├── strategies/            # Strategy CRUD, immutable version snapshots, SHA-256 config hash
│   ├── backtests/             # Asynchronous run queue, tearsheet metrics, trade blotter, equity curve
│   ├── billing/               # Metering compute seconds and AI inference tokens
│   ├── data/                  # OHLCV market data streaming for charts
│   ├── ai/                    # Grounded AI routes (hypothesis-to-spec, backtest critique)
│   ├── worker.py              # Background job dispatcher (Redis/RQ with in-memory thread fallback)
│   └── worker_daemon.py       # Standalone RQ worker process
├── core/                      # Consolidated Causal Quantitative Engine
│   ├── backtesting/           # BaseStrategy, RSIStrategy, DivergenceStrategy, BacktestEngine
│   ├── execution/             # CostModel (slippage bps, commission per trade, spread pips)
│   ├── risk/                  # Position sizing (risk % of capital, stop loss distance)
│   ├── portfolio/             # PortfolioState, TradeRecord, EquityPoint
│   ├── research/              # Market regime detection (volatility regimes & trend strength)
│   ├── data/                  # OHLCV data normalizers, Bar schemas
│   └── ai/                    # Grounded AI (Pydantic schemas, Ollama/Cloud router, critique engine)
├── infrastructure/            # Persistence & Database
│   ├── database/              # SQLAlchemy models, connection manager, data ingestor CLI
│   └── database/alembic/      # Alembic database migrations
├── frontend/                  # Next.js 14 / React 18 / Tailwind / Lightweight-Charts
│   ├── src/components/        # StrategyLab, CandlestickChart, EquityChart, TradeBlotter, AICritiquePanel
│   └── src/app/               # Quant command center page
├── data/                      # Market data (XAUUSD_1H_merged.csv, monthly raw CSVs)
├── docker-compose.yml         # Complete stack (Postgres, Redis, Backend, Worker, Frontend, Ollama)
├── Dockerfile                 # Backend & Worker container
└── run_tests.py               # Complete automated unit & integration test suite
```

---

## 1. Zero-Lookahead Causal Execution Engine

Many retail backtesters suffer from lookahead bias through centered rolling windows (`center=True`) or accessing bar $t$ close prices before the candle actually completes.

QuantEdge eliminates lookahead bias via strictly causal mechanics:
1. **Causal Swing & Pivot Detection**: A swing pivot at bar $k = t - w$ is confirmed **strictly** at bar $t$ only when $w$ subsequent bars have closed above/below bar $k$.
2. **Execution Timing**: Signals generated on closed candle $t$ execute on bar $t+1$ open (or bar $t$ close adjusted for slippage and spread).
3. **Explicit Cost Modeling**:
   $$\text{Entry Price (Long)} = P_{\text{raw}} + \frac{\text{Spread}}{2} + \left(P_{\text{raw}} \times \frac{\text{Slippage (bps)}}{10{,}000}\right)$$
   $$\text{Exit Price (Long)} = P_{\text{raw}} - \frac{\text{Spread}}{2} - \left(P_{\text{raw}} \times \frac{\text{Slippage (bps)}}{10{,}000}\right)$$
   $$\text{Commission} = \text{Commission per trade} + \left(\text{Notional} \times \frac{\text{Commission (bps)}}{10{,}000}\right)$$

---

## 2. Database Schema & Persistence

Managed via **PostgreSQL** and **Alembic**:
- `users`: Identity, authentication, password hashes.
- `workspaces` & `user_workspaces`: Multi-tenant organization boundaries and RBAC (`owner`, `admin`, `member`).
- `strategies` & `strategy_versions`: Immutable parameter snapshots with a deterministic SHA-256 config hash (`code_hash`).
- `backtest_runs`: Status lifecycle (`PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`), cost inputs, and quantitative tearsheet metrics.
- `backtest_trades`: Individual executed orders with net PnL, gross PnL, return %, commissions, slippage, and exit reasons.
- `equity_points`: Mark-to-market equity curve, cash balance, and drawdown trajectory.
- `ohlcv_bars`: Partition-ready store with unique constraint and composite index on `(symbol, timeframe, ts_utc)`.
- `usage_records`: Metering compute execution seconds and AI LLM token usage for billing.

---

## 3. Data Ingestion CLI

Idempotently load raw monthly CSVs or merged datasets into the database:

```bash
# Ingest merged dataset
python infrastructure/database/ingest_data.py --source data/XAUUSD_1H_merged.csv --symbol XAUUSD --timeframe 1H

# Ingest all raw monthly files
python infrastructure/database/ingest_data.py --source "data/xauusd_raw/*.csv" --symbol XAUUSD --timeframe 1H --export-parquet data/XAUUSD_1H.parquet
```

---

## 4. Grounded AI Layer

The AI module rejects hallucinated financial advice and guarantees return predictions:
1. **Strategy-to-Spec Assistant (`POST /ai/hypothesis-to-spec`)**:
   Translates plain-English trading ideas into validated, machine-executable JSON strategy parameters with explicit quantitative bounds. Always sets `human_confirmation_required = True`.
2. **Automated Backtest & Regime Critique (`POST /ai/critique-backtest/{run_id}`)**:
   Analyzes completed runs, citing exact numbers:
   - Evaluates sample size (flags runs with $< 30$ trades).
   - Audits overfitting risk (flags extreme Sharpe ratios or excessive degrees of freedom).
   - Diagnoses max drawdown duration and underwater stagnation.
   - Evaluates regime suitability (Trending Bull, Trending Bear, Ranging, High Volatility).
3. **Hybrid LLM Routing**:
   Supports local **Ollama** models (`qwen2.5:7b`, `llama3.1`) for privacy and local testing, cloud models for production, and deterministic heuristic evaluation fallback when offline.

---

## 5. Quickstart & Local Development

### Prerequisites
- Python 3.10+ (or Python 3.9+)
- Node.js 18+ (for frontend)

### Run Automated Test Suite
```bash
python run_tests.py
```

### Run Root Strategy Backtests
```bash
# RSI Strategy
python rsi_backtest.py

# Divergence Strategy (Early Entry)
python divergence_early_entry.py

# Divergence Strategy (Neckline Breakout)
python divergence_backtest.py
```

### Start Backend Server
```bash
uvicorn main:app --reload --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

---

## 6. Docker Compose Deployment

Run the complete production stack (PostgreSQL, Redis, FastAPI Backend, RQ Worker, Next.js Frontend):

```bash
# Standard Stack
docker compose up -d --build

# Stack with Local Ollama AI Container
docker compose --profile ai up -d --build
```

- **Frontend Research Web App**: `http://localhost:3000`
- **FastAPI REST API**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **PostgreSQL**: `localhost:5432` (`quant` / `quantpass`)
- **Redis Queue**: `localhost:6379`
