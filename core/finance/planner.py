"""Personal Capital, Cash Flow Runway, Goal & Tax-Drag Planning Module

Deterministic calculations for:
- Recurring & irregular cash flows, savings rate, and emergency fund runway
- Debt elimination scenarios (Avalanche vs. Snowball vs. Invest)
- Compounded tax-drag and platform fee-drag modeling over 1 to 10 years
- Goal milestones and capital allocation projections
- Strict quantitative non-advisory compliance notice and grounded AI narrative
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
import numpy as np
from pydantic import BaseModel, Field

from core.ai.provider import LLMProvider


class CashFlowItem(BaseModel):
    name: str = Field(..., description="Description (e.g. Salary, Rent, Healthcare)")
    amount: float = Field(..., description="Amount in currency")
    flow_type: Literal["income", "expense"] = Field(..., description="Cash flow direction")
    frequency: Literal["monthly", "annual", "one_time"] = Field(default="monthly")
    is_fixed: bool = Field(default=True, description="Fixed baseline vs discretionary variable")


class DebtItem(BaseModel):
    name: str = Field(..., description="Debt label (e.g. Credit Card, Student Loan)")
    balance: float = Field(..., ge=0.0)
    interest_rate_pct: float = Field(..., ge=0.0, description="Annual percentage rate APR (e.g. 19.5%)")
    minimum_payment: float = Field(..., ge=0.0)


class FinancialGoal(BaseModel):
    title: str = Field(..., description="Target objective (e.g. Trading Capital Seed, Down Payment)")
    target_amount: float = Field(..., ge=0.0)
    current_savings: float = Field(default=0.0, ge=0.0)
    target_months: int = Field(default=24, ge=1, le=360)


class TaxDragConfig(BaseModel):
    blended_capital_gains_tax_pct: float = Field(default=25.0, ge=0.0, le=60.0, description="Blended short/long term capital gains tax rate")
    annual_fee_drag_pct: float = Field(default=0.75, ge=0.0, le=10.0, description="Annual platform/broker/management fee drag")
    assumed_gross_annual_return_pct: float = Field(default=12.0, ge=-20.0, le=100.0, description="Hypothetical gross annual trading or investment return")


class EmergencyRunwayResult(BaseModel):
    liquid_reserves: float
    monthly_fixed_expenses: float
    monthly_total_expenses: float
    runway_months: float
    health_status: Literal["CRITICAL", "ADEQUATE", "ROBUST"]
    recommended_target_reserve: float
    reserve_deficit_or_surplus: float


class DebtPayoffComparison(BaseModel):
    strategy_name: str
    total_interest_paid: float
    months_to_debt_free: int
    monthly_cash_freed_up: float
    summary: str


class CompoundProjectionYear(BaseModel):
    year: int
    gross_contributions: float
    gross_portfolio_value: float
    net_after_tax_fee_value: float
    annual_tax_drag: float
    cumulative_drag_dollars: float


class FinancialPlanOutput(BaseModel):
    plan_id: str
    as_of_ts: str
    total_monthly_income: float
    total_monthly_expenses: float
    monthly_net_cashflow: float
    savings_rate_pct: float
    emergency_runway: EmergencyRunwayResult
    debt_payoff_scenarios: List[DebtPayoffComparison]
    goal_projections: List[Dict[str, Any]]
    compound_tax_drag_projection: List[CompoundProjectionYear]
    total_10yr_tax_fee_drag_pct: float
    executive_summary: str
    action_plan: List[str]
    disclaimer: str = Field(
        default="This tool provides algorithmic mathematical simulations for personal capital planning and quantitative research only. It does not provide certified financial, legal, tax, or investment advice.",
        description="Compliance non-advisory legal notice"
    )


def calculate_cash_flow_and_runway(
    cash_flows: List[CashFlowItem],
    liquid_reserves: float,
) -> Dict[str, Any]:
    """
    Computes monthly normalized cash flows, savings rate, and emergency runway.
    """
    monthly_income = 0.0
    monthly_fixed_expenses = 0.0
    monthly_variable_expenses = 0.0

    for item in cash_flows:
        # Normalize to monthly
        amt = item.amount
        if item.frequency == "annual":
            monthly_amt = amt / 12.0
        elif item.frequency == "one_time":
            monthly_amt = amt / 12.0  # amortize over year
        else:
            monthly_amt = amt

        if item.flow_type == "income":
            monthly_income += monthly_amt
        else:
            if item.is_fixed:
                monthly_fixed_expenses += monthly_amt
            else:
                monthly_variable_expenses += monthly_amt

    total_expenses = monthly_fixed_expenses + monthly_variable_expenses
    net_cashflow = monthly_income - total_expenses
    savings_rate = (net_cashflow / max(monthly_income, 1e-6)) * 100.0 if monthly_income > 0 else 0.0

    # Runway in months based on fixed baseline expenses
    fixed_denom = max(monthly_fixed_expenses, 1.0)
    runway_months = round(liquid_reserves / fixed_denom, 1)

    if runway_months < 3.0:
        health = "CRITICAL"
    elif runway_months < 6.0:
        health = "ADEQUATE"
    else:
        health = "ROBUST"

    recommended_reserve = round(total_expenses * 6.0, 2)
    reserve_diff = round(liquid_reserves - recommended_reserve, 2)

    runway_res = EmergencyRunwayResult(
        liquid_reserves=round(liquid_reserves, 2),
        monthly_fixed_expenses=round(monthly_fixed_expenses, 2),
        monthly_total_expenses=round(total_expenses, 2),
        runway_months=runway_months,
        health_status=health,
        recommended_target_reserve=recommended_reserve,
        reserve_deficit_or_surplus=reserve_diff,
    )

    return {
        "monthly_income": round(monthly_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cashflow": round(net_cashflow, 2),
        "savings_rate_pct": round(savings_rate, 1),
        "runway": runway_res,
    }


def simulate_debt_payoff(
    debts: List[DebtItem],
    extra_monthly_payment: float = 0.0,
) -> List[DebtPayoffComparison]:
    """
    Simulates Avalanche (highest APR first) vs Snowball (lowest balance first).
    """
    if not debts:
        return [
            DebtPayoffComparison(
                strategy_name="Debt-Free",
                total_interest_paid=0.0,
                months_to_debt_free=0,
                monthly_cash_freed_up=0.0,
                summary="No outstanding debt obligations recorded.",
            )
        ]

    # Helper simulation function
    def run_sim(order_key, reverse=True) -> Dict[str, Any]:
        sim_debts = [
            {"name": d.name, "balance": float(d.balance), "rate": float(d.interest_rate_pct) / 100.0 / 12.0, "min": float(d.minimum_payment)}
            for d in sorted(debts, key=order_key, reverse=reverse)
        ]
        total_interest = 0.0
        months = 0
        max_months = 360

        while any(d["balance"] > 0.01 for d in sim_debts) and months < max_months:
            months += 1
            available_extra = extra_monthly_payment

            # Apply interest & pay minimums
            for d in sim_debts:
                if d["balance"] > 0:
                    interest = d["balance"] * d["rate"]
                    total_interest += interest
                    d["balance"] += interest

                    payment = min(d["balance"], d["min"])
                    d["balance"] -= payment

            # Apply extra snowball/avalanche to top priority debt
            for d in sim_debts:
                if d["balance"] > 0 and available_extra > 0:
                    extra = min(d["balance"], available_extra)
                    d["balance"] -= extra
                    available_extra -= extra

        freed_cash = sum(d.minimum_payment for d in debts)
        return {
            "months": months,
            "total_interest": round(total_interest, 2),
            "freed_cash": round(freed_cash, 2),
        }

    avalanche = run_sim(lambda d: d.interest_rate_pct, reverse=True)
    snowball = run_sim(lambda d: d.balance, reverse=False)

    return [
        DebtPayoffComparison(
            strategy_name="Avalanche (Mathematically Optimal - Highest APR First)",
            total_interest_paid=avalanche["total_interest"],
            months_to_debt_free=avalanche["months"],
            monthly_cash_freed_up=avalanche["freed_cash"],
            summary=f"Debt-free in {avalanche['months']} months with ${avalanche['total_interest']:.2f} total interest paid.",
        ),
        DebtPayoffComparison(
            strategy_name="Snowball (Behavioral Momentum - Lowest Balance First)",
            total_interest_paid=snowball["total_interest"],
            months_to_debt_free=snowball["months"],
            monthly_cash_freed_up=snowball["freed_cash"],
            summary=f"Debt-free in {snowball['months']} months with ${snowball['total_interest']:.2f} total interest paid.",
        ),
    ]


def simulate_compound_tax_drag(
    initial_capital: float,
    monthly_contribution: float,
    tax_cfg: Optional[TaxDragConfig] = None,
    years: int = 10,
) -> List[CompoundProjectionYear]:
    """
    Models compounded growth comparing gross return vs net after-tax & after-fee drag.
    """
    cfg = tax_cfg or TaxDragConfig()
    gross_rate = cfg.assumed_gross_annual_return_pct / 100.0
    tax_rate = cfg.blended_capital_gains_tax_pct / 100.0
    fee_rate = cfg.annual_fee_drag_pct / 100.0

    # Net annual return after taxes on gains and fees
    # Return subject to tax = gross_rate * (1 - tax_rate) - fee_rate
    net_rate = max(-0.50, (gross_rate * (1.0 - tax_rate)) - fee_rate)

    projections: List[CompoundProjectionYear] = []
    gross_val = initial_capital
    net_val = initial_capital
    cum_drag = 0.0
    cum_contributions = initial_capital

    for y in range(1, years + 1):
        annual_contribution = monthly_contribution * 12.0
        cum_contributions += annual_contribution

        # Gross compound
        gross_gains = (gross_val + (annual_contribution / 2.0)) * gross_rate
        gross_val = gross_val + annual_contribution + gross_gains

        # Net compound
        net_gains = (net_val + (annual_contribution / 2.0)) * net_rate
        net_val = net_val + annual_contribution + net_gains

        annual_drag = max(0.0, gross_gains - net_gains)
        cum_drag = gross_val - net_val

        projections.append(
            CompoundProjectionYear(
                year=y,
                gross_contributions=round(cum_contributions, 2),
                gross_portfolio_value=round(gross_val, 2),
                net_after_tax_fee_value=round(net_val, 2),
                annual_tax_drag=round(annual_drag, 2),
                cumulative_drag_dollars=round(cum_drag, 2),
            )
        )

    return projections


def generate_comprehensive_financial_plan(
    cash_flows: List[CashFlowItem],
    liquid_reserves: float,
    debts: Optional[List[DebtItem]] = None,
    goals: Optional[List[FinancialGoal]] = None,
    tax_config: Optional[TaxDragConfig] = None,
    provider: Optional[LLMProvider] = None,
) -> FinancialPlanOutput:
    """
    Builds the full grounded personal capital, cash flow, debt payoff, and tax drag plan.
    """
    plan_id = str(uuid.uuid4())
    cf_res = calculate_cash_flow_and_runway(cash_flows, liquid_reserves)
    debt_res = simulate_debt_payoff(debts or [], extra_monthly_payment=max(0.0, cf_res["net_cashflow"] * 0.3))
    
    monthly_investable = max(0.0, cf_res["net_cashflow"] * 0.5)
    tax_cfg = tax_config or TaxDragConfig()
    tax_projections = simulate_compound_tax_drag(
        initial_capital=max(1000.0, liquid_reserves * 0.3),
        monthly_contribution=monthly_investable,
        tax_cfg=tax_cfg,
        years=10,
    )

    # Goal Milestones
    goal_projections: List[Dict[str, Any]] = []
    if goals:
        for g in goals:
            deficit = max(0.0, g.target_amount - g.current_savings)
            needed_monthly = round(deficit / max(g.target_months, 1), 2)
            feasible = cf_res["net_cashflow"] >= needed_monthly
            goal_projections.append({
                "title": g.title,
                "target_amount": g.target_amount,
                "current_savings": g.current_savings,
                "target_months": g.target_months,
                "needed_monthly_contribution": needed_monthly,
                "feasible_with_current_cashflow": feasible,
            })

    # Drag calculations
    y10 = tax_projections[-1]
    drag_pct = round((y10.cumulative_drag_dollars / max(y10.gross_portfolio_value, 1e-6)) * 100.0, 1)

    # Grounded narrative synthesis
    rw = cf_res["runway"]
    exec_summary = (
        f"Financial Capital Plan: Monthly net cashflow is ${cf_res['net_cashflow']:.2f} "
        f"({cf_res['savings_rate_pct']:.1f}% savings rate). Liquid emergency runway stands at "
        f"{rw.runway_months} months ({rw.health_status}). "
        f"10-year compounding under {tax_cfg.assumed_gross_annual_return_pct}% gross return yields "
        f"${y10.net_after_tax_fee_value:,.2f} net (absorbing ${y10.cumulative_drag_dollars:,.2f} in tax & fee friction, {drag_pct}% drag)."
    )

    action_plan = [
        f"Maintain emergency cash runway of at least 6 months (${rw.recommended_target_reserve:,.2f})." if rw.health_status != "ROBUST" else "Emergency runway is robust (> 6 months). Direct excess cash flow to capital deployment.",
        f"Direct monthly surplus to Avalanche debt payoff to eliminate ${debt_res[0].total_interest_paid:.2f} in interest drag." if debts and debt_res[0].months_to_debt_free > 0 else "Debt-free status maintained. Full surplus available for investment.",
        f"Utilize tax-advantaged accounts or loss-harvesting to mitigate the projected {drag_pct}% 10-year tax drag.",
    ]

    return FinancialPlanOutput(
        plan_id=plan_id,
        as_of_ts=datetime.now(timezone.utc).isoformat(),
        total_monthly_income=cf_res["monthly_income"],
        total_monthly_expenses=cf_res["total_expenses"],
        monthly_net_cashflow=cf_res["net_cashflow"],
        savings_rate_pct=cf_res["savings_rate_pct"],
        emergency_runway=rw,
        debt_payoff_scenarios=debt_res,
        goal_projections=goal_projections,
        compound_tax_drag_projection=tax_projections,
        total_10yr_tax_fee_drag_pct=drag_pct,
        executive_summary=exec_summary,
        action_plan=action_plan,
    )
