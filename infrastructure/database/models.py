"""Relational Database Models for QuantEdge Platform

Includes Users, Workspaces, Strategies, Versioned Configs, Backtest Runs,
Trades, Equity Series, Market Data OHLCV Bars, and Billing Usage.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    Integer,
    BigInteger,
    Index,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import json

Base = declarative_base()


# SQLite compatible JSON and UUID types
class SafeJSON(TypeDecorator):
    """Platform-independent JSON type. Uses JSONB on PostgreSQL, Text on SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type. Uses PostgreSQL UUID or CHAR(36) on others."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
            return value


# =========================================================================
# 1. Identity & Organization Models
# =========================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owned_workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete")
    workspace_memberships = relationship("UserWorkspace", back_populates="user", cascade="all, delete")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete")
    backtest_runs = relationship("BacktestRun", back_populates="user", cascade="all, delete")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete")
    committee_reports = relationship("CommitteeReport", back_populates="user", cascade="all, delete")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    owner_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("UserWorkspace", back_populates="workspace", cascade="all, delete")
    strategies = relationship("Strategy", back_populates="workspace", cascade="all, delete")
    backtest_runs = relationship("BacktestRun", back_populates="workspace", cascade="all, delete")
    usage_records = relationship("UsageRecord", back_populates="workspace", cascade="all, delete")
    committee_reports = relationship("CommitteeReport", back_populates="workspace", cascade="all, delete")


class UserWorkspace(Base):
    __tablename__ = "user_workspaces"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), default="member", nullable=False)  # "owner", "admin", "member"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="workspace_memberships")
    workspace = relationship("Workspace", back_populates="members")

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace"),
    )


# =========================================================================
# 2. Strategy & Immutable Version Snapshots
# =========================================================================

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(64), nullable=False, default="rsi")  # "rsi", "divergence"
    is_live = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="strategies")
    user = relationship("User", back_populates="strategies")
    versions = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete", order_by="StrategyVersion.version_number")


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(GUID(), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False)
    parameters = Column(SafeJSON, nullable=False)
    code_hash = Column(String(128), nullable=False)  # SHA-256 of canonical params & logic
    is_locked = Column(Boolean, default=True, nullable=False)  # Immutable snapshot

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    strategy = relationship("Strategy", back_populates="versions")
    backtest_runs = relationship("BacktestRun", back_populates="strategy_version", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("strategy_id", "version_number", name="uq_strategy_version_number"),
        Index("idx_strategy_version_hash", "strategy_id", "code_hash"),
    )


# =========================================================================
# 3. Backtest Runs, Executed Trades & Equity Curve
# =========================================================================

class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    strategy_version_id = Column(GUID(), ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    config_hash = Column(String(128), nullable=False)

    symbol = Column(String(32), nullable=False, default="XAUUSD")
    timeframe = Column(String(16), nullable=False, default="1H")

    start_ts = Column(DateTime(timezone=True))
    end_ts = Column(DateTime(timezone=True))

    initial_capital = Column(Float, nullable=False, default=10000.0)
    final_equity = Column(Float)

    # Cost model parameters
    slippage_bps = Column(Float, default=1.0)
    commission_per_trade = Column(Float, default=0.0)
    spread_pips = Column(Float, default=0.0)

    # Core Quant Performance Metrics
    total_return = Column(Float)
    cagr = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    calmar_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)

    error_message = Column(Text)
    logs = Column(SafeJSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    strategy_version = relationship("StrategyVersion", back_populates="backtest_runs")
    workspace = relationship("Workspace", back_populates="backtest_runs")
    user = relationship("User", back_populates="backtest_runs")
    trades = relationship("BacktestTrade", back_populates="backtest_run", cascade="all, delete", order_by="BacktestTrade.trade_number")
    equity_points = relationship("EquityPointModel", back_populates="backtest_run", cascade="all, delete", order_by="EquityPointModel.ts")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    backtest_run_id = Column(GUID(), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    trade_number = Column(Integer, nullable=False)
    symbol = Column(String(32), nullable=False)
    side = Column(String(16), nullable=False)  # "long" or "short"

    entry_ts = Column(DateTime(timezone=True), nullable=False)
    exit_ts = Column(DateTime(timezone=True), nullable=False)

    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)

    pnl = Column(Float, nullable=False)
    gross_pnl = Column(Float, nullable=False)
    return_pct = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)

    exit_reason = Column(String(64), nullable=False)
    bars_held = Column(Integer, nullable=False)

    backtest_run = relationship("BacktestRun", back_populates="trades")


class EquityPointModel(Base):
    __tablename__ = "equity_points"

    id = Column(Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True)
    backtest_run_id = Column(GUID(), ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    equity = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    drawdown = Column(Float, nullable=False)
    drawdown_pct = Column(Float, nullable=False)
    returns = Column(Float, default=0.0)

    backtest_run = relationship("BacktestRun", back_populates="equity_points")


# =========================================================================
# 4. Market Data Store (Partition-Ready OHLCV Bars)
# =========================================================================

class OHLCVBar(Base):
    __tablename__ = "ohlcv_bars"

    id = Column(Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    timeframe = Column(String(16), nullable=False)
    ts_utc = Column(DateTime(timezone=True), nullable=False)

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0.0)
    source = Column(String(64), default="raw_csv")

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "ts_utc", name="uq_symbol_tf_ts"),
        Index("idx_ohlcv_symbol_tf_ts", "symbol", "timeframe", "ts_utc"),
    )


# =========================================================================
# 5. Billing & Usage Metering
# =========================================================================

class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False)  # "backtest_execution", "ai_strategy_translation", "ai_backtest_critique"
    units = Column(Float, nullable=False)             # compute seconds or token count
    unit_type = Column(String(32), nullable=False)    # "seconds", "tokens"
    cost_cents = Column(Float, default=0.0)
    metadata_json = Column(SafeJSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="usage_records")
    user = relationship("User", back_populates="usage_records")


# =========================================================================
# 6. Multi-Agent Committee Evaluations & Reports
# =========================================================================

class CommitteeReport(Base):
    __tablename__ = "committee_reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_version_id = Column(GUID(), ForeignKey("strategy_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    backtest_run_id = Column(GUID(), ForeignKey("backtest_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    symbol = Column(String(32), nullable=False, default="XAUUSD")
    timeframe = Column(String(16), nullable=False, default="1H")
    as_of_ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    executive_summary = Column(Text, nullable=False)
    portfolio_action = Column(String(16), nullable=False)  # BUY, SELL, HOLD
    overall_confidence = Column(Float, nullable=False, default=0.7)
    human_confirmation_required = Column(Boolean, default=True, nullable=False)

    report_json = Column(SafeJSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="committee_reports")
    user = relationship("User", back_populates="committee_reports")
    strategy_version = relationship("StrategyVersion")
    backtest_run = relationship("BacktestRun")


# =========================================================================
# 7. Pillar 1: Market Catalysts & Scheduled Events
# =========================================================================

class MarketCatalyst(Base):
    __tablename__ = "market_catalysts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(32), nullable=False, default="ALL", index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, default="macro")  # macro, rates, liquidity, earnings, geopolitical
    impact = Column(String(16), nullable=False, default="HIGH")     # HIGH, MEDIUM, LOW
    sentiment = Column(String(16), nullable=False, default="NEUTRAL") # HAWKISH, DOVISH, BULLISH, BEARISH, NEUTRAL

    actual_value = Column(String(64))
    forecast_value = Column(String(64))
    previous_value = Column(String(64))
    source = Column(String(128), default="Economic Calendar")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_catalyst_symbol_ts", "symbol", "timestamp_utc"),
    )


# =========================================================================
# 8. Pillar 2: Execution & Risk Rule Profiles
# =========================================================================

class RiskRuleProfileModel(Base):
    __tablename__ = "risk_rule_profiles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False, default="Standard Institutional Discipline")
    max_risk_per_trade_pct = Column(Float, nullable=False, default=0.01)
    daily_loss_limit_pct = Column(Float, nullable=False, default=0.03)
    daily_loss_limit_abs = Column(Float)
    max_drawdown_pct = Column(Float, nullable=False, default=0.15)
    drawdown_mode = Column(String(32), nullable=False, default="trailing")  # static, trailing
    max_consecutive_losses = Column(Integer, nullable=False, default=3)
    cooldown_bars = Column(Integer, nullable=False, default=12)
    max_trades_per_day = Column(Integer, nullable=False, default=5)
    max_gross_exposure_pct = Column(Float, nullable=False, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# =========================================================================
# 9. Pillar 3: Walk-Forward Validation & Stress Testing Runs
# =========================================================================

class WalkForwardRun(Base):
    __tablename__ = "walk_forward_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    strategy_type = Column(String(64), nullable=False, default="rsi")
    symbol = Column(String(32), nullable=False, default="XAUUSD")
    timeframe = Column(String(16), nullable=False, default="1H")
    mode = Column(String(32), nullable=False, default="rolling")  # rolling, anchored

    num_windows = Column(Integer, nullable=False)
    overall_wfe = Column(Float, nullable=False)
    parameter_stability_score = Column(Float, nullable=False)
    robustness_verdict = Column(String(32), nullable=False)  # ROBUST, BORDERLINE, OVERFIT

    summary_verdict = Column(Text, nullable=False)
    config_json = Column(SafeJSON, nullable=False)
    results_json = Column(SafeJSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# =========================================================================
# 10. Pillar 5: Personal Capital, Cash Flow & Goal Plans
# =========================================================================

class CashflowPlanModel(Base):
    __tablename__ = "cashflow_plans"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False, default="Primary Capital Plan")
    monthly_net_cashflow = Column(Float, nullable=False)
    savings_rate_pct = Column(Float, nullable=False)
    emergency_runway_months = Column(Float, nullable=False)
    health_status = Column(String(32), nullable=False)  # CRITICAL, ADEQUATE, ROBUST
    total_10yr_tax_fee_drag_pct = Column(Float, nullable=False)

    plan_json = Column(SafeJSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


