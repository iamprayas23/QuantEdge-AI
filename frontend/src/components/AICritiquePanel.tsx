import React, { useState } from "react";
import { StrategySpecOutput, BacktestCritiqueOutput } from "@/types";
import { Sparkles, Brain, AlertTriangle, CheckCircle, ArrowRight, ShieldCheck, Zap } from "lucide-react";

interface AICritiquePanelProps {
  onApplySpec: (params: Record<string, any>) => void;
  onParseHypothesis: (prompt: string) => Promise<StrategySpecOutput>;
  onCritiqueRun: () => Promise<BacktestCritiqueOutput>;
  hasCompletedRun: boolean;
}

export const AICritiquePanel: React.FC<AICritiquePanelProps> = ({
  onApplySpec,
  onParseHypothesis,
  onCritiqueRun,
  hasCompletedRun,
}) => {
  const [activeTab, setActiveTab] = useState<"hypothesis" | "critique">("hypothesis");
  const [prompt, setPrompt] = useState<string>(
    "Trade XAUUSD 1H with RSI period 14, enter long when RSI crosses below 28, 1.5 ATR stop loss, 2.5 risk reward, 1% risk per trade"
  );
  const [spec, setSpec] = useState<StrategySpecOutput | null>(null);
  const [critique, setCritique] = useState<BacktestCritiqueOutput | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateSpec = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await onParseHypothesis(prompt);
      setSpec(res);
    } catch (err: any) {
      setError(err.message || "Failed to generate strategy specification");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCritique = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await onCritiqueRun();
      setCritique(res);
    } catch (err: any) {
      setError(err.message || "Failed to critique backtest run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 flex flex-col space-y-3">
      {/* Tab Switcher */}
      <div className="flex items-center justify-between pb-2 border-b border-surfaceBorder">
        <div className="flex items-center space-x-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-xs font-mono font-bold text-white tracking-wider">
            GROUNDED QUANT AI CO-PILOT
          </span>
        </div>

        <div className="flex items-center space-x-1 text-xs font-mono bg-[#0f1422] p-0.5 rounded border border-surfaceBorder">
          <button
            onClick={() => setActiveTab("hypothesis")}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === "hypothesis" ? "bg-purple-600 text-white font-bold" : "text-gray-400 hover:text-white"
            }`}
          >
            Hypothesis Assistant
          </button>
          <button
            onClick={() => setActiveTab("critique")}
            className={`px-2.5 py-1 rounded transition-colors ${
              activeTab === "critique" ? "bg-purple-600 text-white font-bold" : "text-gray-400 hover:text-white"
            }`}
          >
            Backtest & Regime Critique
          </button>
        </div>
      </div>

      {error && (
        <div className="text-xs font-mono text-rose-400 bg-rose-950/50 border border-rose-800 p-2.5 rounded">
          {error}
        </div>
      )}

      {/* Tab 1: Hypothesis-to-Spec Assistant */}
      {activeTab === "hypothesis" && (
        <div className="flex flex-col space-y-3 text-xs font-mono">
          <div>
            <label className="text-gray-400 block mb-1">
              Natural Language Trading Hypothesis / Trading Rules:
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Enter long when RSI drops below 30 on 1H gold, exit on 2:1 RR or when RSI exceeds 70..."
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded p-2.5 text-white focus:outline-none focus:border-purple-500 font-mono text-xs"
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleGenerateSpec}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{loading ? "Translating Hypothesis..." : "Generate Machine Spec"}</span>
            </button>
          </div>

          {spec && (
            <div className="bg-[#0c1018] border border-purple-900/60 rounded-lg p-3 space-y-2 mt-2">
              <div className="flex items-center justify-between">
                <span className="text-purple-300 font-bold uppercase tracking-wider text-[11px]">
                  Validated Machine Spec ({spec.strategy_type.toUpperCase()})
                </span>
                <button
                  onClick={() => onApplySpec(spec.parameters)}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold"
                >
                  <span>Apply to Strategy Lab</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              <div className="text-gray-300 text-[11px]">
                {spec.hypothesis_summary}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
                {Object.entries(spec.parameters).map(([k, v]) => (
                  <div key={k} className="bg-[#141a29] border border-surfaceBorder p-1.5 rounded">
                    <span className="text-gray-400 block text-[10px]">{k}</span>
                    <span className="text-white font-bold">{String(v)}</span>
                  </div>
                ))}
              </div>

              {spec.validation_findings.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-purple-900/40">
                  {spec.validation_findings.map((f, i) => (
                    <div key={i} className="flex items-start space-x-1.5 text-[10px] text-amber-300">
                      <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>{f.message} {f.recommendation}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Grounded Backtest & Regime Critique */}
      {activeTab === "critique" && (
        <div className="flex flex-col space-y-3 text-xs font-mono">
          {!hasCompletedRun ? (
            <div className="text-gray-400 text-center py-6 bg-[#0c1018] rounded border border-surfaceBorder">
              Launch and complete a backtest run first to generate evidence-grounded AI critique.
            </div>
          ) : (
            <>
              <div className="flex justify-between items-center">
                <span className="text-gray-300">
                  Analyze completed backtest metrics, drawdown clusters, and regime performance.
                </span>
                <button
                  onClick={handleGenerateCritique}
                  disabled={loading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white font-bold"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>{loading ? "Synthesizing Critique..." : "Generate Grounded Critique"}</span>
                </button>
              </div>

              {critique && (
                <div className="space-y-3 mt-2">
                  {/* Executive Summary */}
                  <div className="bg-[#0c1018] border border-surfaceBorder p-3 rounded-lg">
                    <div className="text-[11px] font-bold text-white mb-1">
                      EXECUTIVE AUDIT SUMMARY
                    </div>
                    <div className="text-gray-300 text-[11px] leading-relaxed">
                      {critique.executive_summary}
                    </div>
                  </div>

                  {/* Overfitting & Drawdown Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Overfitting */}
                    <div className="bg-[#0c1018] border border-surfaceBorder p-3 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-bold text-white">OVERFITTING RISK</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                            critique.overfitting_analysis.risk_level === "LOW"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : critique.overfitting_analysis.risk_level === "MODERATE"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-rose-950 text-rose-400 border border-rose-800"
                          }`}
                        >
                          {critique.overfitting_analysis.risk_level} RISK
                        </span>
                      </div>
                      <div className="text-gray-300 text-[11px]">
                        {critique.overfitting_analysis.rationale}
                      </div>
                    </div>

                    {/* Drawdown Assessment */}
                    <div className="bg-[#0c1018] border border-surfaceBorder p-3 rounded-lg">
                      <div className="text-[11px] font-bold text-white mb-1">
                        UNDERWATER & TAIL RISK
                      </div>
                      <div className="text-gray-300 text-[11px]">
                        {critique.drawdown_critique.recovery_assessment}
                      </div>
                    </div>
                  </div>

                  {/* Regime Suitability */}
                  <div className="bg-[#0c1018] border border-surfaceBorder p-3 rounded-lg">
                    <div className="text-[11px] font-bold text-white mb-2">
                      REGIME SUITABILITY MATRIX
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      {critique.regime_breakdown.map((r, i) => (
                        <div key={i} className="bg-[#141a29] border border-surfaceBorder p-2 rounded">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-white text-[10px]">{r.regime}</span>
                            <span
                              className={`text-[9px] px-1 py-0.2 rounded font-bold ${
                                r.suitability === "FAVORABLE"
                                  ? "text-emerald-400"
                                  : r.suitability === "NEUTRAL"
                                  ? "text-blue-400"
                                  : "text-rose-400"
                              }`}
                            >
                              {r.suitability}
                            </span>
                          </div>
                          <p className="text-gray-400 text-[10px] leading-tight">
                            {r.observed_metric_note}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div className="bg-[#0c1018] border border-surfaceBorder p-3 rounded-lg">
                    <div className="text-[11px] font-bold text-white mb-1.5">
                      ACTIONABLE QUANT RECOMMENDATIONS
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px]">
                      {critique.actionable_recommendations.map((rec, i) => (
                        <li key={i} className="flex items-start space-x-1.5">
                          <CheckCircle className="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" />
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Regulatory / Compliance Notice */}
      <div className="text-[10px] text-gray-500 font-mono pt-1 text-center">
        QuantEdge Grounded AI operates with strict numerical citations. No forward returns are guaranteed.
      </div>
    </div>
  );
};
