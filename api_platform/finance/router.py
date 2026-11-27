"""Personal Finance Router (Pillar 5: Capital Planning, Runway, Debt Payoff & Tax-Drag)"""
from uuid import UUID
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace, CashflowPlanModel
from api_platform.auth.dependencies import get_current_user, get_current_workspace
from api_platform.billing.service import record_usage
from core.finance.planner import (
    CashFlowItem,
    DebtItem,
    FinancialGoal,
    TaxDragConfig,
    FinancialPlanOutput,
    generate_comprehensive_financial_plan,
)

router = APIRouter(prefix="/finance", tags=["Personal Capital & Financial Planning"])


class PlanRequest(BaseModel):
    name: str = Field(default="Primary Capital & Runway Plan")
    liquid_reserves: float = Field(default=25000.0, ge=0.0)
    cash_flows: List[CashFlowItem] = Field(default_factory=list)
    debts: List[DebtItem] = Field(default_factory=list)
    goals: List[FinancialGoal] = Field(default_factory=list)
    tax_config: Optional[TaxDragConfig] = None


@router.post("/plan", response_model=FinancialPlanOutput)
def calculate_plan(
    payload: PlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Simulates personal cash flows, emergency runway, debt payoff, and 10-year compound tax drag.
    """
    # Provide sensible defaults if empty
    flows = payload.cash_flows
    if not flows:
        flows = [
            CashFlowItem(name="Base Professional Salary", amount=8500.0, flow_type="income", frequency="monthly", is_fixed=True),
            CashFlowItem(name="Trading Allocation Withdrawal", amount=1500.0, flow_type="income", frequency="monthly", is_fixed=False),
            CashFlowItem(name="Housing (Mortgage/Rent)", amount=2600.0, flow_type="expense", frequency="monthly", is_fixed=True),
            CashFlowItem(name="Living & Baseline Utilities", amount=1400.0, flow_type="expense", frequency="monthly", is_fixed=True),
            CashFlowItem(name="Discretionary & Technology", amount=900.0, flow_type="expense", frequency="monthly", is_fixed=False),
        ]

    debts = payload.debts
    if not debts:
        debts = [
            DebtItem(name="Revolving Credit Card", balance=4500.0, interest_rate_pct=21.5, minimum_payment=150.0),
            DebtItem(name="Education / Student Loan", balance=18000.0, interest_rate_pct=5.5, minimum_payment=220.0),
        ]

    goals = payload.goals
    if not goals:
        goals = [
            FinancialGoal(title="Prop Firm / Institutional Trading Seed", target_amount=50000.0, current_savings=15000.0, target_months=18),
            FinancialGoal(title="Capital Reserve Runway Extension", target_amount=30000.0, current_savings=25000.0, target_months=12),
        ]

    plan = generate_comprehensive_financial_plan(
        cash_flows=flows,
        liquid_reserves=payload.liquid_reserves,
        debts=debts,
        goals=goals,
        tax_config=payload.tax_config,
    )

    # Meter usage
    record_usage(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        event_type="financial_planning_simulation",
        units=300.0,
        unit_type="tokens",
        cost_cents=0.5,
        metadata={"plan_id": plan.plan_id},
    )

    return plan


@router.post("/plans/save")
def save_plan(
    payload: PlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Calculates and persists a financial plan in the database."""
    plan_out = calculate_plan(payload, db=db, current_user=current_user, workspace=workspace)

    plan_row = CashflowPlanModel(
        workspace_id=workspace.id,
        user_id=current_user.id,
        name=payload.name,
        monthly_net_cashflow=plan_out.monthly_net_cashflow,
        savings_rate_pct=plan_out.savings_rate_pct,
        emergency_runway_months=plan_out.emergency_runway.runway_months,
        health_status=plan_out.emergency_runway.health_status,
        total_10yr_tax_fee_drag_pct=plan_out.total_10yr_tax_fee_drag_pct,
        plan_json=plan_out.model_dump(),
    )
    db.add(plan_row)
    db.commit()
    db.refresh(plan_row)
    return {"id": str(plan_row.id), "status": "saved", "plan": plan_out}


@router.get("/plans")
def list_plans(
    limit: int = 10,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Lists saved financial plans for the workspace."""
    plans = (
        db.query(CashflowPlanModel)
        .filter(CashflowPlanModel.workspace_id == workspace.id)
        .order_by(CashflowPlanModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "monthly_net_cashflow": p.monthly_net_cashflow,
            "savings_rate_pct": p.savings_rate_pct,
            "emergency_runway_months": p.emergency_runway_months,
            "health_status": p.health_status,
            "total_10yr_tax_fee_drag_pct": p.total_10yr_tax_fee_drag_pct,
            "created_at": p.created_at.isoformat(),
        }
        for p in plans
    ]
