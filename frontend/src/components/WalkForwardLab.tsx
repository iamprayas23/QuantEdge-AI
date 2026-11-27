"use client";

import React, { useState } from "react";
import { WalkForwardAnalysisResult, StressTestReport, Strategy } from "@/types";
import { api } from "@/lib/api";
import {
  RotateCcw,
  Activity,
  ShieldAlert,
  CheckCircle,
  AlertTriangle,
  Play,
  Layers,
  Zap,
} from "lucide-react";

interface WalkForwardLabProps {
  selectedStrategy: Strategy | null;
}

export const WalkForwardLab: React.FC<WalkForwardLabProps> = ({ selectedStrategy }) => {
  const [activeTab, setActiveTab] = useState<"walk_forward" | "stress">("walk_forward");
  const [trainBars, setTrainBars] = useState<number>(300);
  const [testBars, setTestBars] = useState<number>(100);
  const [stepBars, setStepBars] = useState<number>(100);
  const [mode, setMode] = useState<"rolling" | "anchored">("rolling");

  const [wfResult, setWfResult] = useState<WalkForwardAnalysisResult | null>(null);
  const [stressReports, setStressReports] = useState<StressTestReport[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunWalkForward = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runWalkForward({
        strategy_type: selectedStrategy?.strategy_type || "rsi",
        symbol: "XAUUSD",
        timeframe: "1H",
        train_bars: trainBars,
        test_bars: testBars,
        step_bars: stepBars,
        mode: mode,
      });
      setWfResult(res);
    } catch (e: any) {
      setError(e.message || "Failed to execute walk-forward validation");
    } finally {
      setLoading(false);
    }
  };

  const handleRunStress = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.runStressTest({
        strategy_type: selectedStrategy?.strategy_type || "rsi",
        symbol: "XAUUSD",
        timeframe: "1H",
        strategy_version_id: selectedStrategy?.latest_version?.id,
        limit_bars: 500,
      });
      setStressReports(res);
    } catch (e: any) {
      setError(e.message || "Failed to execute stress testing battery");
    } finally {
      setLoading(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    if (verdict === "ROBUST") {
      return (
        <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
          <CheckCircle className="w-3.5 h-3.5" /> ROBUST
        </span>
      );
    }
    if (verdict === "BORDERLINE") {
      return (
        <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5" /> BORDERLINE
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 text-xs font-bold rounded bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
        <ShieldAlert className="w-3.5 h-3.5" /> OVERFIT
      </span>
    );
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 space-y-4 font-mono">
      {/* Header & Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <RotateCcw className="w-4 h-4 text-purple-400" />
          <span className="text-xs font-bold text-white tracking-wider">
            PILLAR 3: WALK-FORWARD OPTIMIZATION & STRESS LAB
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
            Out-of-Sample Verification
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <div className="flex items-center bg-[#0f1422] p-0.5 rounded border border-surfaceBorder text-xs">
            <button
              onClick={() => setActiveTab("walk_forward")}
              className={`px-2.5 py-1 rounded transition ${
                activeTab === "walk_forward" ? "bg-purple-600 text-white font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              Walk-Forward Analysis
            </button>
            <button
              onClick={() => setActiveTab("stress")}
              className={`px-2.5 py-1 rounded transition ${
                activeTab === "stress" ? "bg-purple-600 text-white font-bold" : "text-gray-400 hover:text-white"
              }`}
            >
              Stress Testing Battery
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* --- TAB 1: Walk-Forward Analysis --- */}
      {activeTab === "walk_forward" && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 bg-[#0b0e17] p-3 rounded-lg border border-surfaceBorder text-xs items-center">
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                className="w-full bg-[#121829] border border-surfaceBorder rounded px-2 py-1 text-white"
              >
                <option value="rolling">Rolling Window</option>
                <option value="anchored">Anchored (Expanding)</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">Train Bars (IS)</label>
              <input
                type="number"
                value={trainBars}
                onChange={(e) => setTrainBars(Number(e.target.value))}
                className="w-full bg-[#121829] border border-surfaceBorder rounded px-2 py-1 text-white"
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">Test Bars (OOS)</label>
              <input
                type="number"
                value={testBars}
                onChange={(e) => setTestBars(Number(e.target.value))}
                className="w-full bg-[#121829] border border-surfaceBorder rounded px-2 py-1 text-white"
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-400 block mb-1">Step Progression</label>
              <input
                type="number"
                value={stepBars}
                onChange={(e) => setStepBars(Number(e.target.value))}
                className="w-full bg-[#121829] border border-surfaceBorder rounded px-2 py-1 text-white"
              />
            </div>
            <div className="col-span-2 sm:col-span-1 pt-3 sm:pt-0">
              <button
                onClick={handleRunWalkForward}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-1.5 py-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white rounded font-bold transition shadow-sm"
              >
                {loading ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Play className="w-3 h-3" />
                    <span>Run Walk-Forward</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Summary */}
          {wfResult && (
            <div className="p-3.5 bg-[#0b0e17] border border-purple-900/60 rounded-lg space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-surfaceBorder/60 pb-2 gap-2">
                <div>
                  <span className="text-xs font-bold text-white uppercase flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-purple-400" />
                    Walk-Forward Generalization Verdict
                  </span>
                  <span className="text-[10px] text-gray-400">
                    Windows Evaluated: <span className="text-white font-bold">{wfResult.num_windows} Folds</span> ({wfResult.mode})
                  </span>
                </div>
                {getVerdictBadge(wfResult.robustness_verdict)}
              </div>

              <p className="text-xs text-gray-200 leading-relaxed">
                {wfResult.summary_verdict}
              </p>

              {/* KPI Multipliers */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#121829] p-2.5 rounded border border-surfaceBorder/50 text-[11px]">
                <div>
                  <span className="text-gray-400 block text-[10px]">Overall WFE Ratio</span>
                  <span className={`text-base font-bold ${wfResult.overall_wfe >= 0.55 ? "text-emerald-400" : "text-rose-400"}`}>
                    {wfResult.overall_wfe}x
                  </span>
                </div>
                <div>
                  <span className="text-gray-400 block text-[10px]">Parameter Stability</span>
                  <span className="text-base text-purple-300 font-bold">{wfResult.parameter_stability_score}%</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-[10px]">Avg OOS Sharpe</span>
                  <span className="text-base text-white font-bold">{wfResult.stitched_oos_summary.avg_oos_sharpe}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-[10px]">Total OOS Trades</span>
                  <span className="text-base text-gray-300 font-bold">{wfResult.stitched_oos_summary.total_oos_trades} Trades</span>
                </div>
              </div>

              {/* Windows Table */}
              <div className="overflow-x-auto border border-surfaceBorder rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0f1422] text-gray-400 border-b border-surfaceBorder text-[10px] uppercase">
                    <tr>
                      <th className="p-2">Fold #</th>
                      <th className="p-2">Selected Parameters</th>
                      <th className="p-2 text-right">IS Sharpe (Train)</th>
                      <th className="p-2 text-right">OOS Sharpe (Test)</th>
                      <th className="p-2 text-right">Fold WFE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surfaceBorder/40">
                    {wfResult.windows.map((w) => (
                      <tr key={w.window_index} className="hover:bg-surfaceHover/40 transition">
                        <td className="p-2 font-bold text-white">Fold {w.window_index + 1}</td>
                        <td className="p-2 text-[10px] text-gray-300 font-mono">
                          {Object.entries(w.selected_params).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(", ")}
                        </td>
                        <td className="p-2 text-right text-gray-400 font-mono">{w.is_metrics.sharpe_ratio}</td>
                        <td className="p-2 text-right font-bold font-mono text-purple-300">{w.oos_metrics.sharpe_ratio}</td>
                        <td className="p-2 text-right font-bold font-mono">
                          <span className={w.wfe >= 0.5 ? "text-emerald-400" : "text-amber-400"}>
                            {w.wfe}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!wfResult && !loading && (
            <div className="py-6 text-center text-xs text-gray-400 border border-dashed border-surfaceBorder rounded-lg">
              Click &quot;Run Walk-Forward&quot; to test your strategy parameters across rolling In-Sample vs Out-of-Sample folds.
            </div>
          )}
        </div>
      )}

      {/* --- TAB 2: Stress Testing Battery --- */}
      {activeTab === "stress" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-[#0b0e17] p-3 rounded-lg border border-surfaceBorder text-xs">
            <span className="text-gray-300">
              Execute institutional shock battery (2.5x slippage, 3x spread widening, execution crisis, and gap shocks).
            </span>
            <button
              onClick={handleRunStress}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white rounded font-bold transition shadow-sm"
            >
              {loading ? (
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5" />
                  <span>Run Stress Battery</span>
                </>
              )}
            </button>
          </div>

          {stressReports.length > 0 && (
            <div className="space-y-2">
              <div className="overflow-x-auto border border-surfaceBorder rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0f1422] text-gray-400 border-b border-surfaceBorder text-[10px] uppercase">
                    <tr>
                      <th className="p-2">Shock Scenario</th>
                      <th className="p-2">Sharpe (Base vs Stressed)</th>
                      <th className="p-2">Max DD Expansion</th>
                      <th className="p-2">Equity Erosion</th>
                      <th className="p-2">Verdict</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surfaceBorder/40">
                    {stressReports.map((sc, i) => (
                      <tr key={i} className="hover:bg-surfaceHover/40 transition">
                        <td className="p-2">
                          <span className="font-bold text-white block">{sc.scenario_name}</span>
                          <span className="text-[10px] text-gray-400 block">{sc.description}</span>
                        </td>
                        <td className="p-2 font-mono">
                          <span className="text-gray-400">{sc.base_sharpe}</span>{" "}
                          <span className="text-gray-500">&rarr;</span>{" "}
                          <span className={sc.stressed_sharpe > 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                            {sc.stressed_sharpe}
                          </span>
                        </td>
                        <td className="p-2 font-mono text-amber-400 font-bold">
                          +{sc.drawdown_expansion_pct}% ({sc.stressed_max_dd}%)
                        </td>
                        <td className="p-2 font-mono text-rose-400 font-bold">
                          -{sc.equity_erosion_pct}%
                        </td>
                        <td className="p-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            sc.status === "PASS" ? "bg-emerald-950 text-emerald-300 border-emerald-800" :
                            sc.status === "DEGRADED" ? "bg-amber-950 text-amber-300 border-amber-800" :
                            "bg-rose-950 text-rose-300 border-rose-800"
                          }`}>
                            {sc.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {stressReports.length === 0 && !loading && (
            <div className="py-6 text-center text-xs text-gray-400 border border-dashed border-surfaceBorder rounded-lg">
              Click &quot;Run Stress Battery&quot; to test your strategy against extreme market shocks and liquidity voids.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
