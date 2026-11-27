"""add finance pillars tables (market_catalysts, risk_rule_profiles, walk_forward_runs, cashflow_plans)

Revision ID: 0003_add_finance_pillars
Revises: 0002_add_committee_reports
Create Date: 2026-11-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_finance_pillars'
down_revision: Union[str, None] = '0002_add_committee_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. market_catalysts
    op.create_table(
        'market_catalysts',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('timestamp_utc', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(32), nullable=False, server_default='ALL'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('category', sa.String(64), nullable=False, server_default='macro'),
        sa.Column('impact', sa.String(16), nullable=False, server_default='HIGH'),
        sa.Column('sentiment', sa.String(16), nullable=False, server_default='NEUTRAL'),
        sa.Column('actual_value', sa.String(64), nullable=True),
        sa.Column('forecast_value', sa.String(64), nullable=True),
        sa.Column('previous_value', sa.String(64), nullable=True),
        sa.Column('source', sa.String(128), server_default='Economic Calendar'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_catalyst_symbol_ts', 'market_catalysts', ['symbol', 'timestamp_utc'])

    # 2. risk_rule_profiles
    op.create_table(
        'risk_rule_profiles',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('max_risk_per_trade_pct', sa.Float(), nullable=False, server_default='0.01'),
        sa.Column('daily_loss_limit_pct', sa.Float(), nullable=False, server_default='0.03'),
        sa.Column('daily_loss_limit_abs', sa.Float(), nullable=True),
        sa.Column('max_drawdown_pct', sa.Float(), nullable=False, server_default='0.15'),
        sa.Column('drawdown_mode', sa.String(32), nullable=False, server_default='trailing'),
        sa.Column('max_consecutive_losses', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('cooldown_bars', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('max_trades_per_day', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_gross_exposure_pct', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_risk_rule_workspace', 'risk_rule_profiles', ['workspace_id'])

    # 3. walk_forward_runs
    op.create_table(
        'walk_forward_runs',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_type', sa.String(64), nullable=False, server_default='rsi'),
        sa.Column('symbol', sa.String(32), nullable=False, server_default='XAUUSD'),
        sa.Column('timeframe', sa.String(16), nullable=False, server_default='1H'),
        sa.Column('mode', sa.String(32), nullable=False, server_default='rolling'),
        sa.Column('num_windows', sa.Integer(), nullable=False),
        sa.Column('overall_wfe', sa.Float(), nullable=False),
        sa.Column('parameter_stability_score', sa.Float(), nullable=False),
        sa.Column('robustness_verdict', sa.String(32), nullable=False),
        sa.Column('summary_verdict', sa.Text(), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('results_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_walk_forward_workspace', 'walk_forward_runs', ['workspace_id'])

    # 4. cashflow_plans
    op.create_table(
        'cashflow_plans',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('monthly_net_cashflow', sa.Float(), nullable=False),
        sa.Column('savings_rate_pct', sa.Float(), nullable=False),
        sa.Column('emergency_runway_months', sa.Float(), nullable=False),
        sa.Column('health_status', sa.String(32), nullable=False),
        sa.Column('total_10yr_tax_fee_drag_pct', sa.Float(), nullable=False),
        sa.Column('plan_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_cashflow_plans_workspace', 'cashflow_plans', ['workspace_id'])


def downgrade() -> None:
    op.drop_table('cashflow_plans')
    op.drop_table('walk_forward_runs')
    op.drop_table('risk_rule_profiles')
    op.drop_table('market_catalysts')
