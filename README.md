# QuantEdge-AI

Modular quantitative strategy backtesting engine, FastAPI platform, and risk analytics workspace.

## Architecture
- `api_platform/`: FastAPI services (`auth`, `strategies`, `backtests`, `users`, `billing`)
- `core/`: Deterministic backtesting engines, signal generators, risk & portfolio modules
- `infrastructure/`: PostgreSQL/SQLAlchemy models, connection management, Docker & logging configs
- `data/`: Historical market OHLCV datasets and ingestion utilities
