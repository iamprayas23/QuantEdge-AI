"use client";

import React, { useState } from "react";
import { FinancialPlanOutput, CashFlowItem, DebtItem, FinancialGoal } from "@/types";
import { api } from "@/lib/api";
import {
  Wallet,
  DollarSign,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  Scale,
  Sparkles,
} from "lucide-react";

export const CashflowPlannerPanel: React.FC = () => {
  const [liquidReserves, setLiquidReserves] = useState<number>(25000);
  const [plan, setPlan] = useState<FinancialPlanOutput | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleCalculatePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.calculateFinancePlan({
        name: "Institutional Trader Personal Capital Plan",
        liquid_reserves: liquidReserves,
      });
      setPlan(res);
    } catch (e: any) {
      setError(e.message || "Failed to simulate capital plan");
    } finally {
      setLoading(false);
    }
  };

  const getHealthBadge = (health: string) => {
    if (health === "ROBUST") {
      return (
        <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
          <CheckCircle className="w-3.5 h-3.5" /> ROBUST (&gt;6m)
        </span>
      );
    }
    if (health === "ADEQUATE") {
      return (
        <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5" /> ADEQUATE (3-6m)
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
        <AlertTriangle className="w-3.5 h-3.5" /> CRITICAL (&lt;3m)
      </span>
    );
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <Wallet className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold text-white tracking-wider">
            PILLAR 5: PERSONAL CAPITAL, CASH FLOW & TAX-DRAG PLANNER
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
            Runway & Tax Drag Simulator
          </span>
        </div>

        <button
          onClick={handleCalculatePlan}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded text-xs font-bold transition shadow-sm"
        >
          {loading ? (
            <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5" />
              <span>Simulate Capital Plan</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Reserves Input Bar */}
      <div className="flex items-center space-x-3 bg-[#0b0e17] p-3 rounded-lg border border-surfaceBorder text-xs">
        <span className="text-gray-400">Current Liquid Cash Reserves:</span>
        <div className="flex items-center space-x-1">
          <span className="text-gray-500">$</span>
          <input
            type="number"
            value={liquidReserves}
            onChange={(e) => setLiquidReserves(Number(e.target.value))}
            className="w-32 bg-[#121829] border border-surfaceBorder rounded px-2 py-1 text-white font-bold"
          />
        </div>
        <span className="text-[10px] text-gray-500 hidden sm:inline">
          (High-yield savings, checking, and unencumbered trading cash buffer)
        </span>
      </div>

      {plan && (
        <div className="space-y-4">
          {/* Executive Summary */}
          <div className="p-3.5 bg-[#0b0e17] border border-emerald-900/60 rounded-lg space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-surfaceBorder/60 pb-2 gap-2">
              <span className="text-xs font-bold text-white uppercase flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Capital Planning Assessment
              </span>
              {getHealthBadge(plan.emergency_runway.health_status)}
            </div>

            <p className="text-xs text-gray-200 leading-relaxed">
              {plan.executive_summary}
            </p>

            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#121829] p-2.5 rounded border border-surfaceBorder/50 text-[11px]">
              <div>
                <span className="text-gray-400 block text-[10px]">Monthly Net Cash Flow</span>
                <span className="text-emerald-400 font-bold text-base">+${plan.monthly_net_cashflow.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px]">Savings Rate</span>
                <span className="text-cyan-300 font-bold text-base">{plan.savings_rate_pct}%</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px]">Emergency Runway</span>
                <span className="text-purple-300 font-bold text-base">{plan.emergency_runway.runway_months} Months</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px]">10-Yr Tax & Fee Drag</span>
                <span className="text-amber-400 font-bold text-base">{plan.total_10yr_tax_fee_drag_pct}% Friction</span>
              </div>
            </div>
          </div>

          {/* Debt Payoff & Goals Comparison */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Debt Elimination */}
            <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 space-y-2">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-amber-400" />
                Debt Payoff Comparison (Avalanche vs Snowball)
              </span>
              <div className="space-y-1.5 text-[11px]">
                {plan.debt_payoff_scenarios.map((sc, i) => (
                  <div key={i} className="bg-[#121829] p-2 rounded border border-surfaceBorder/40">
                    <div className="flex items-center justify-between font-bold text-white mb-0.5">
                      <span>{sc.strategy_name}</span>
                      <span className="text-amber-400">${sc.total_interest_paid.toFixed(2)} Interest</span>
                    </div>
                    <span className="text-gray-400 block text-[10px]">{sc.summary}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Goal Projections */}
            <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 space-y-2">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
                Target Goal Feasibility
              </span>
              <div className="space-y-1.5 text-[11px]">
                {plan.goal_projections.map((g, i) => (
                  <div key={i} className="bg-[#121829] p-2 rounded border border-surfaceBorder/40">
                    <div className="flex items-center justify-between font-bold text-white mb-0.5">
                      <span>{g.title}</span>
                      <span className={g.feasible_with_current_cashflow ? "text-emerald-400" : "text-rose-400"}>
                        {g.feasible_with_current_cashflow ? "FEASIBLE" : "DEFICIT"}
                      </span>
                    </div>
                    <div className="text-[10px] text-gray-400 flex justify-between">
                      <span>Target: ${g.target_amount.toLocaleString()} in {g.target_months}m</span>
                      <span>Needed: ${g.needed_monthly_contribution.toFixed(2)}/mo</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 10-Year Compounded Tax Drag Table */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-gray-300">
              10-YEAR COMPOUNDED CAPITAL GROWTH & TAX-DRAG TRAJECTORY
            </span>
            <div className="overflow-x-auto border border-surfaceBorder rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0f1422] text-gray-400 border-b border-surfaceBorder text-[10px] uppercase">
                  <tr>
                    <th className="p-2">Year</th>
                    <th className="p-2 text-right">Cumulative Principal</th>
                    <th className="p-2 text-right">Gross Portfolio Value</th>
                    <th className="p-2 text-right">Net After-Tax & Fees</th>
                    <th className="p-2 text-right">Cumulative Drag ($)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surfaceBorder/40">
                  {plan.compound_tax_drag_projection.map((pt) => (
                    <tr key={pt.year} className="hover:bg-surfaceHover/40 transition">
                      <td className="p-2 font-bold text-white">Year {pt.year}</td>
                      <td className="p-2 text-right text-gray-400 font-mono">${pt.gross_contributions.toLocaleString()}</td>
                      <td className="p-2 text-right text-gray-200 font-mono font-bold">${pt.gross_portfolio_value.toLocaleString()}</td>
                      <td className="p-2 text-right text-emerald-400 font-mono font-bold">${pt.net_after_tax_fee_value.toLocaleString()}</td>
                      <td className="p-2 text-right text-amber-400 font-mono">-${pt.cumulative_drag_dollars.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Compliance Disclaimer */}
          <div className="p-2.5 bg-[#0e111a] border border-surfaceBorder rounded text-[10px] text-gray-500 text-center">
            {plan.disclaimer}
          </div>
        </div>
      )}

      {!plan && !loading && (
        <div className="py-6 text-center text-xs text-gray-400 border border-dashed border-surfaceBorder rounded-lg">
          Click &quot;Simulate Capital Plan&quot; to project your emergency runway, debt elimination avalanche, and 10-year compounded tax friction.
        </div>
      )}
    </div>
  );
};
