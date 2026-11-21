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

# Mount Routers
app.include_router(auth_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(billing_router)
app.include_router(data_router)
app.include_router(ai_router)


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
