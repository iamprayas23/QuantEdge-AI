"use client";

import React, { useState } from "react";
import {
  CommitteeReviewOutput,
  Strategy,
  BacktestRun,
  AnalystSignal,
} from "@/types";
import {
  Users,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  ShieldAlert,
  Sliders,
  Sparkles,
  Zap,
} from "lucide-react";

interface CommitteePanelProps {
  onApplyProposal: (params: Record<string, any>) => void;
  onConveneCommittee: (params: {
    symbol: string;
    timeframe: string;
    strategyVersionId?: string;
    backtestRunId?: string;
  }) => Promise<CommitteeReviewOutput>;
  selectedStrategy: Strategy | null;
  activeRun: BacktestRun | null;
}

export const CommitteePanel: React.FC<CommitteePanelProps> = ({
  onApplyProposal,
  onConveneCommittee,
  selectedStrategy,
  activeRun,
}) => {
  const [review, setReview] = useState<CommitteeReviewOutput | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [humanConfirmed, setHumanConfirmed] = useState<boolean>(false);
  const [appliedSuccess, setAppliedSuccess] = useState<boolean>(false);

  const handleConvene = async () => {
    setLoading(true);
    setError(null);
    setAppliedSuccess(false);
    try {
      const res = await onConveneCommittee({
        symbol: "XAUUSD",
        timeframe: "1H",
        strategyVersionId: selectedStrategy?.latest_version?.id,
        backtestRunId: activeRun?.id,
      });
      setReview(res);
    } catch (err: any) {
      setError(err.message || "Failed to convene committee");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (!review || !humanConfirmed) return;
    onApplyProposal(review.portfolio_proposal.recommended_parameters);
    setAppliedSuccess(true);
    setTimeout(() => setAppliedSuccess(false), 4000);
  };

  const getSignalBadge = (sig: string) => {
    if (sig === "BULLISH") {
      return (
        <span className="px-2 py-0.5 text-xs font-bold rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> BULLISH
        </span>
      );
    }
    if (sig === "BEARISH") {
      return (
        <span className="px-2 py-0.5 text-xs font-bold rounded bg-rose-950 text-rose-400 border border-rose-800 flex items-center gap-1">
          <TrendingDown className="w-3 h-3" /> BEARISH
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-950 text-amber-400 border border-amber-800">
        NEUTRAL
      </span>
    );
  };

  const getGateBadge = (action: string) => {
    if (action === "PERMIT") {
      return (
        <span className="px-2 py-0.5 text-xs font-bold rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3" /> PERMIT
        </span>
      );
    }
    if (action === "RESTRICT") {
      return (
        <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-950 text-amber-400 border border-amber-800 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" /> RESTRICT
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs font-bold rounded bg-rose-950 text-rose-400 border border-rose-800 flex items-center gap-1">
        <ShieldAlert className="w-3 h-3" /> HALT
      </span>
    );
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 flex flex-col space-y-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <Users className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono font-bold text-white tracking-wider">
            MULTI-AGENT QUANT COMMITTEE
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
            ai-hedge-fund / quantedge
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {activeRun && (
            <span className="text-[11px] font-mono text-gray-400">
              Run: <span className="text-white font-bold">{activeRun.id.slice(0, 8)}</span>
            </span>
          )}
          <button
            onClick={handleConvene}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded text-xs font-mono font-bold transition shadow-sm"
          >
            {loading ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Convene Committee</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* When no review has been run yet */}
      {!review && !loading && (
        <div className="py-10 text-center flex flex-col items-center justify-center space-y-2 text-gray-400">
          <Users className="w-8 h-8 text-cyan-500/50" />
          <p className="text-xs font-mono">
            Convene the 4-agent committee (Technicals, Regime, Risk Manager, and Portfolio Manager)
            to synthesize deterministic signals and enforce capital guardrails.
          </p>
        </div>
      )}

      {/* Committee Review Content */}
      {review && (
        <div className="space-y-4">
          {/* Executive Summary Banner */}
          <div className="p-3 bg-[#0f1422] border border-cyan-900/50 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-[11px] font-mono text-cyan-400 font-bold uppercase tracking-wider">
                  Committee Consensus ({review.symbol} • {review.timeframe})
                </span>
                <span className="text-[10px] font-mono text-gray-400">
                  {new Date(review.as_of_ts).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs font-mono text-gray-200 leading-relaxed">
                {review.executive_summary}
              </p>
            </div>

            <div className="flex sm:flex-col items-end justify-center pl-2 border-t sm:border-t-0 sm:border-l border-surfaceBorder pt-2 sm:pt-0">
              <span className="text-[10px] font-mono text-gray-400 mb-0.5">DECISION</span>
              <span
                className={`text-sm font-mono font-bold px-3 py-1 rounded ${
                  review.portfolio_proposal.target_action === "BUY"
                    ? "bg-emerald-900 text-emerald-300 border border-emerald-700"
                    : review.portfolio_proposal.target_action === "SELL"
                    ? "bg-rose-900 text-rose-300 border border-rose-700"
                    : "bg-amber-900 text-amber-300 border border-amber-700"
                }`}
              >
                {review.portfolio_proposal.target_action}
              </span>
            </div>
          </div>

          {/* 4 Agent Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* 1. Technicals Agent */}
            {review.analyst_signals.technicals && (
              <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 flex flex-col space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
                    <span className="text-xs font-mono font-bold text-white">Technicals Analyst</span>
                  </div>
                  {getSignalBadge(review.analyst_signals.technicals.signal)}
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-gray-400">
                  <span>Confidence:</span>
                  <span className="text-white font-bold">
                    {(review.analyst_signals.technicals.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-blue-500 h-full rounded-full"
                    style={{ width: `${review.analyst_signals.technicals.confidence * 100}%` }}
                  />
                </div>

                {/* Grounded Metrics */}
                <div className="grid grid-cols-3 gap-1 bg-[#121829] p-2 rounded text-[10px] font-mono border border-surfaceBorder/50">
                  <div>
                    <span className="text-gray-400">Close: </span>
                    <span className="text-white font-bold">
                      {review.analyst_signals.technicals.metrics_grounding.last_close}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">RSI: </span>
                    <span className="text-white font-bold">
                      {review.analyst_signals.technicals.metrics_grounding.rsi14}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">ATR: </span>
                    <span className="text-white font-bold">
                      {review.analyst_signals.technicals.metrics_grounding.atr14}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">EMA50: </span>
                    <span className="text-white">
                      {review.analyst_signals.technicals.metrics_grounding.ema50}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-400">EMA200: </span>
                    <span className="text-white">
                      {review.analyst_signals.technicals.metrics_grounding.ema200}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] font-mono text-gray-300 leading-snug">
                  {review.analyst_signals.technicals.rationale}
                </p>
              </div>
            )}

            {/* 2. Regime & Volatility Agent */}
            {review.analyst_signals.regime && (
              <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 flex flex-col space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5">
                    <Zap className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-xs font-mono font-bold text-white">Regime Analyst</span>
                  </div>
                  {getSignalBadge(review.analyst_signals.regime.signal)}
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-gray-400">
                  <span>Confidence:</span>
                  <span className="text-white font-bold">
                    {(review.analyst_signals.regime.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-purple-500 h-full rounded-full"
                    style={{ width: `${review.analyst_signals.regime.confidence * 100}%` }}
                  />
                </div>

                {/* Grounded Metrics */}
                <div className="grid grid-cols-2 gap-1 bg-[#121829] p-2 rounded text-[10px] font-mono border border-surfaceBorder/50">
                  <div>
                    <span className="text-gray-400">Vol Regime: </span>
                    <span className="text-purple-300 font-bold uppercase">
                      {review.analyst_signals.regime.metrics_grounding.vol_regime?.replace("_", " ")}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Trend Regime: </span>
                    <span className="text-purple-300 font-bold uppercase">
                      {review.analyst_signals.regime.metrics_grounding.trend_regime?.replace("_", " ")}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-400">Realized Vol (Annualized): </span>
                    <span className="text-white font-bold">
                      {review.analyst_signals.regime.metrics_grounding.realized_vol_pct}%
                    </span>
                  </div>
                </div>

                <p className="text-[11px] font-mono text-gray-300 leading-snug">
                  {review.analyst_signals.regime.rationale}
                </p>
              </div>
            )}

            {/* 3. Risk Manager Agent */}
            <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-xs font-mono font-bold text-white">Risk Manager (CRO Gate)</span>
                </div>
                {getGateBadge(review.risk_assessment.allowed_action)}
              </div>

              <div className="grid grid-cols-2 gap-2 bg-[#121829] p-2 rounded text-[10px] font-mono border border-surfaceBorder/50">
                <div>
                  <span className="text-gray-400">Max Risk / Trade: </span>
                  <span className="text-amber-400 font-bold">
                    {(review.risk_assessment.max_risk_per_trade_pct * 100).toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">DD Threshold: </span>
                  <span className="text-white font-bold">
                    {review.risk_assessment.max_drawdown_limit_pct}%
                  </span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-400">Assessment: </span>
                  <span className="text-gray-200">
                    {review.risk_assessment.volatility_assessment}
                  </span>
                </div>
              </div>

              {review.risk_assessment.risk_warnings.length > 0 && (
                <div className="space-y-1">
                  {review.risk_assessment.risk_warnings.map((w, idx) => (
                    <div
                      key={idx}
                      className="flex items-start space-x-1.5 text-[10px] font-mono text-amber-300 bg-amber-950/40 p-1.5 rounded border border-amber-900/60"
                    >
                      <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}

              <p className="text-[11px] font-mono text-gray-300 leading-snug">
                {review.risk_assessment.rationale}
              </p>
            </div>

            {/* 4. Portfolio Manager Synthesis */}
            <div className="bg-[#0b0e17] border border-surfaceBorder rounded-lg p-3 flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5">
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-xs font-mono font-bold text-white">Portfolio Manager (CIO)</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {review.portfolio_proposal.execution_urgency} URGENCY
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 bg-[#121829] p-2 rounded text-[10px] font-mono border border-surfaceBorder/50">
                <div>
                  <span className="text-gray-400">Target Allocation: </span>
                  <span className="text-cyan-400 font-bold">
                    {review.portfolio_proposal.target_allocation_pct}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Risk per Trade: </span>
                  <span className="text-white font-bold">
                    {(review.portfolio_proposal.risk_per_trade_pct * 100).toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">SL ATR Mult: </span>
                  <span className="text-white font-bold">
                    {review.portfolio_proposal.stop_loss_atr_mult}x
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">TP ATR Mult: </span>
                  <span className="text-white font-bold">
                    {review.portfolio_proposal.take_profit_atr_mult}x
                  </span>
                </div>
              </div>

              <p className="text-[11px] font-mono text-gray-300 leading-snug">
                {review.portfolio_proposal.reasoning}
              </p>
            </div>
          </div>

          {/* Action Approval & Human Confirmation Card */}
          <div className="bg-[#0f1422] border border-surfaceBorder rounded-lg p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="humanConfirm"
                checked={humanConfirmed}
                onChange={(e) => setHumanConfirmed(e.target.checked)}
                className="w-4 h-4 rounded border-gray-700 bg-gray-900 text-cyan-500 focus:ring-cyan-600 focus:ring-offset-gray-900 cursor-pointer"
              />
              <label htmlFor="humanConfirm" className="text-xs font-mono text-gray-200 cursor-pointer">
                I verify and acknowledge the committee proposal (Human Sign-off Required)
              </label>
            </div>

            <div className="flex items-center space-x-2">
              {appliedSuccess && (
                <span className="text-xs font-mono text-emerald-400 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Applied to Strategy Lab!
                </span>
              )}
              <button
                onClick={handleApply}
                disabled={!humanConfirmed || review.portfolio_proposal.target_action === "HOLD" && review.risk_assessment.allowed_action === "HALT"}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded text-xs font-mono font-bold transition shadow-sm"
              >
                <span>Apply Proposal to Strategy Lab</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Compliance Disclaimer */}
          <div className="text-[10px] font-mono text-gray-400 text-center">
            {review.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
};
