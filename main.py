"""QuantEdge Unified FastAPI Application"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from infrastructure.database.connection import engine
from infrastructure.database.models import Base
from api_platform.auth.router import router as auth_router
from api_platform.strategies.router import router as strategy_router
from api_platform.backtests.router import router as backtest_router
from api_platform.billing.router import router as billing_router
from api_platform.data.router import router as data_router
from api_platform.ai.router import router as ai_router
from api_platform.research.router import router as research_router
from api_platform.risk.router import router as risk_router
from api_platform.finance.router import router as finance_router

# Auto-create tables if running in development mode
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: could not run Base.metadata.create_all (will rely on Alembic/migrations): {e}")

app = FastAPI(
    title="QuantEdge API",
    description="Grounded Quantitative Backtesting, Strategy Research & AI Platform",
    version="0.2.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    from infrastructure.database.connection import SessionLocal
    from api_platform.auth.service import create_user_with_workspace
    from api_platform.strategies.service import create_strategy
    from infrastructure.database.models import User, Strategy

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "trader@quantedge.io").first()
        if not user:
            res = create_user_with_workspace(db, "trader@quantedge.io", "QuantPassword123!", "Alpha Quant Labs")
            if res:
                u, ws = res
                create_strategy(
                    db,
                    ws.id,
                    u.id,
                    "Gold RSI Mean Reversion",
                    "Institutional 1H mean-reversion with volatility ATR stops",
                    "rsi",
                )
                create_strategy(
                    db,
                    ws.id,
                    u.id,
                    "XAUUSD Divergence Causal",
                    "Strictly causal regular divergence with ATR risk management",
                    "divergence",
                )
    except Exception as err:
        print(f"Startup seed notice: {err}")
    finally:
        db.close()


# Mount Routers
app.include_router(auth_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(billing_router)
app.include_router(data_router)
app.include_router(ai_router)
app.include_router(research_router)
app.include_router(risk_router)
app.include_router(finance_router)


@app.get("/")
def root():
    return {
        "platform": "QuantEdge",
        "status": "online",
        "version": "0.2.0",
        "docs_url": "/docs",
    }


@app.get("/health")
def healthcheck():
    return {"status": "healthy"}
