"""add committee_reports table

Revision ID: 0002_add_committee_reports
Revises: 0001_initial_schema
Create Date: 2026-11-22 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_add_committee_reports'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'committee_reports',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('workspace_id', sa.CHAR(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.CHAR(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_version_id', sa.CHAR(36), sa.ForeignKey('strategy_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('backtest_run_id', sa.CHAR(36), sa.ForeignKey('backtest_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('symbol', sa.String(32), nullable=False, server_default='XAUUSD'),
        sa.Column('timeframe', sa.String(16), nullable=False, server_default='1H'),
        sa.Column('as_of_ts', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('portfolio_action', sa.String(16), nullable=False),
        sa.Column('overall_confidence', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('human_confirmation_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('report_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_committee_reports_workspace_id', 'committee_reports', ['workspace_id'])
    op.create_index('idx_committee_reports_strategy_version', 'committee_reports', ['strategy_version_id'])
    op.create_index('idx_committee_reports_backtest_run', 'committee_reports', ['backtest_run_id'])


def downgrade() -> None:
    op.drop_index('idx_committee_reports_backtest_run', table_name='committee_reports')
    op.drop_index('idx_committee_reports_strategy_version', table_name='committee_reports')
    op.drop_index('idx_committee_reports_workspace_id', table_name='committee_reports')
    op.drop_table('committee_reports')
