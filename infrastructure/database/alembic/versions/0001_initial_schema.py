"""initial normalized schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-21 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # 2. Workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('owner_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_workspaces_slug', 'workspaces', ['slug'])

    # 3. User Workspaces
    op.create_table(
        'user_workspaces',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(32), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'workspace_id', name='uq_user_workspace')
    )

    # 4. Strategies
    op.create_table(
        'strategies',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_type', sa.String(64), nullable=False, server_default='rsi'),
        sa.Column('is_live', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_strategies_workspace', 'strategies', ['workspace_id'])

    # 5. Strategy Versions
    op.create_table(
        'strategy_versions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('strategy_id', sa.CHAR(36), sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('parameters', sa.Text(), nullable=False),
        sa.Column('code_hash', sa.String(128), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('strategy_id', 'version_number', name='uq_strategy_version_number')
    )
    op.create_index('idx_strategy_version_hash', 'strategy_versions', ['strategy_id', 'code_hash'])

    # 6. Backtest Runs
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('strategy_version_id', sa.CHAR(36), sa.ForeignKey('strategy_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('config_hash', sa.String(128), nullable=False),
        sa.Column('symbol', sa.String(32), nullable=False, server_default='XAUUSD'),
        sa.Column('timeframe', sa.String(16), nullable=False, server_default='1H'),
        sa.Column('start_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('initial_capital', sa.Float(), nullable=False, server_default='10000.0'),
        sa.Column('final_equity', sa.Float(), nullable=True),
        sa.Column('slippage_bps', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('commission_per_trade', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('spread_pips', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('total_return', sa.Float(), nullable=True),
        sa.Column('cagr', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('calmar_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_backtest_runs_version', 'backtest_runs', ['strategy_version_id'])
    op.create_index('idx_backtest_runs_workspace', 'backtest_runs', ['workspace_id'])
    op.create_index('idx_backtest_runs_status', 'backtest_runs', ['status'])

    # 7. Backtest Trades
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('backtest_run_id', sa.CHAR(36), sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trade_number', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('side', sa.String(16), nullable=False),
        sa.Column('entry_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('gross_pnl', sa.Float(), nullable=False),
        sa.Column('return_pct', sa.Float(), nullable=False),
        sa.Column('commission', sa.Float(), server_default='0.0'),
        sa.Column('slippage', sa.Float(), server_default='0.0'),
        sa.Column('exit_reason', sa.String(64), nullable=False),
        sa.Column('bars_held', sa.Integer(), nullable=False),
    )
    op.create_index('idx_backtest_trades_run', 'backtest_trades', ['backtest_run_id'])

    # 8. Equity Points
    op.create_table(
        'equity_points',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('backtest_run_id', sa.CHAR(36), sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('equity', sa.Float(), nullable=False),
        sa.Column('cash', sa.Float(), nullable=False),
        sa.Column('drawdown', sa.Float(), nullable=False),
        sa.Column('drawdown_pct', sa.Float(), nullable=False),
        sa.Column('returns', sa.Float(), server_default='0.0'),
    )
    op.create_index('idx_equity_points_run_ts', 'equity_points', ['backtest_run_id', 'ts'])

    # 9. OHLCV Bars
    op.create_table(
        'ohlcv_bars',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(32), nullable=False),
        sa.Column('timeframe', sa.String(16), nullable=False),
        sa.Column('ts_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source', sa.String(64), server_default='raw_csv'),
        sa.UniqueConstraint('symbol', 'timeframe', 'ts_utc', name='uq_symbol_tf_ts'),
    )
    op.create_index('idx_ohlcv_symbol_tf_ts', 'ohlcv_bars', ['symbol', 'timeframe', 'ts_utc'])

    # 10. Usage Records
    op.create_table(
        'usage_records',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('units', sa.Float(), nullable=False),
        sa.Column('unit_type', sa.String(32), nullable=False),
        sa.Column('cost_cents', sa.Float(), server_default='0.0'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_usage_records_workspace', 'usage_records', ['workspace_id'])
    op.create_index('idx_usage_records_user', 'usage_records', ['user_id'])


def downgrade() -> None:
    op.drop_table('usage_records')
    op.drop_table('ohlcv_bars')
    op.drop_table('equity_points')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('strategy_versions')
    op.drop_table('strategies')
    op.drop_table('user_workspaces')
    op.drop_table('workspaces')
    op.drop_table('users')
