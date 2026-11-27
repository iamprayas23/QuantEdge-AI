"use client";

import React, { useState, useEffect } from "react";
import { RiskRuleProfile, GuardrailAuditReport, BacktestRun } from "@/types";
import { api } from "@/lib/api";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Sliders,
  DollarSign,
  TrendingUp,
  Activity,
  ArrowRight,
} from "lucide-react";

interface RiskGuardrailsPanelProps {
  activeRun: BacktestRun | null;
}

export const RiskGuardrailsPanel: React.FC<RiskGuardrailsPanelProps> = ({ activeRun }) => {
  const [profiles, setProfiles] = useState<RiskRuleProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<RiskRuleProfile | null>(null);
  const [auditReport, setAuditReport] = useState<GuardrailAuditReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    try {
      const data = await api.listRiskProfiles();
      setProfiles(data);
      if (data.length > 0) setSelectedProfile(data[0]);
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleRunAudit = async () => {
    if (!activeRun) {
      setError("Please execute or select a completed backtest run to audit.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rep = await api.auditBacktestRules(activeRun.id, selectedProfile?.id);
      setAuditReport(rep);
    } catch (e: any) {
      setError(e.message || "Failed to audit backtest rules");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold text-white tracking-wider">
            PILLAR 2: RULE DISCIPLINE & EXECUTION GUARDRAILS
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
            Emotional Drift Prevention
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleRunAudit}
            disabled={loading || !activeRun}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded text-xs font-bold transition shadow-sm"
          >
            {loading ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Auditing Blotter...</span>
              </>
            ) : (
              <>
                <Sliders className="w-3.5 h-3.5" />
                <span>Audit Active Backtest</span>
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

      {/* Profile Parameters Cards */}
      {selectedProfile && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 bg-[#0b0e17] p-3 rounded-lg border border-surfaceBorder text-xs">
          <div>
            <span className="text-gray-400 block text-[10px]">Max Risk / Trade</span>
            <span className="text-white font-bold">{(selectedProfile.max_risk_per_trade_pct * 100).toFixed(1)}%</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px]">Daily Loss Limit</span>
            <span className="text-amber-400 font-bold">{(selectedProfile.daily_loss_limit_pct * 100).toFixed(1)}%</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px]">Trailing Max DD</span>
            <span className="text-rose-400 font-bold">{(selectedProfile.max_drawdown_pct * 100).toFixed(1)}%</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px]">Loss Cooldown</span>
            <span className="text-purple-300 font-bold">{selectedProfile.max_consecutive_losses} Losses ({selectedProfile.cooldown_bars}b)</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px]">Max Trades / Day</span>
            <span className="text-cyan-300 font-bold">{selectedProfile.max_trades_per_day} Executions</span>
          </div>
        </div>
      )}

      {/* Audit Report Results */}
      {auditReport && (
        <div className="p-3.5 bg-[#0b0e17] border border-emerald-900/60 rounded-lg space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-surfaceBorder/60 pb-2 gap-2">
            <div>
              <span className="text-xs font-bold text-white uppercase flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Rule Discipline Audit Verdict
              </span>
              <span className="text-[10px] text-gray-400">
                Profile: <span className="text-emerald-300 font-bold">{auditReport.profile_name}</span>
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] text-gray-400">Adherence Score:</span>
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded border ${
                auditReport.rule_adherence_score >= 85 ? "bg-emerald-950 text-emerald-300 border-emerald-800" :
                auditReport.rule_adherence_score >= 70 ? "bg-amber-950 text-amber-300 border-amber-800" :
                "bg-rose-950 text-rose-300 border-rose-800"
              }`}>
                {auditReport.rule_adherence_score}%
              </span>
            </div>
          </div>

          <p className="text-xs text-gray-200 leading-relaxed">
            {auditReport.summary_recommendation}
          </p>

          {/* Counterfactual Alpha Preserved Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#121829] p-2.5 rounded border border-surfaceBorder/50 text-[11px]">
            <div>
              <span className="text-gray-400 block text-[10px]">Total Trades Audited</span>
              <span className="text-white font-bold">{auditReport.total_trades_evaluated} ({auditReport.compliant_trades} Compliant)</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Rule Breaches Detected</span>
              <span className="text-rose-400 font-bold">{auditReport.breach_count} Breaches</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Lost to Emotional Drift</span>
              <span className="text-rose-400 font-bold">-${auditReport.capital_lost_to_breaches.toFixed(2)}</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Disciplined Alpha Preserved</span>
              <span className="text-emerald-400 font-bold">+${auditReport.disciplined_alpha_preserved.toFixed(2)}</span>
            </div>
          </div>

          {/* Breaches List */}
          {auditReport.detailed_breaches.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-gray-400 uppercase">Audit Trail • Rule Violations</span>
              <div className="max-h-48 overflow-y-auto space-y-1 text-[11px]">
                {auditReport.detailed_breaches.map((b, i) => (
                  <div key={i} className="flex items-start space-x-2 bg-rose-950/30 border border-rose-900/50 p-2 rounded">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-[10px] text-gray-400">
                        <span className="font-bold text-rose-300 uppercase">{b.rule_name}</span>
                        <span>{new Date(b.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <p className="text-gray-300">{b.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!auditReport && !loading && (
        <div className="py-6 text-center text-xs text-gray-400 border border-dashed border-surfaceBorder rounded-lg">
          Select a completed backtest run and click &quot;Audit Active Backtest&quot; to test your execution against the institutional rule profile.
        </div>
      )}
    </div>
  );
};
