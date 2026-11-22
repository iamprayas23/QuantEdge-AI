import React, { useState } from "react";
import { Strategy, StrategyVersion } from "@/types";
import { Play, Save, History, Sliders, CheckCircle2, AlertCircle } from "lucide-react";

interface StrategyLabProps {
  strategies: Strategy[];
  selectedStrategy: Strategy | null;
  onSelectStrategy: (s: Strategy) => void;
  onLaunchBacktest: (params: {
    versionId: string;
    symbol: string;
    timeframe: string;
    initialCapital: number;
    slippageBps: number;
    commission: number;
    spreadPips: number;
    riskPct: number;
  }) => Promise<void>;
  onSaveNewVersion: (params: Record<string, any>) => Promise<void>;
  isExecuting: boolean;
  externalParamsToApply?: Record<string, any> | null;
}

export const StrategyLab: React.FC<StrategyLabProps> = ({
  strategies,
  selectedStrategy,
  onSelectStrategy,
  onLaunchBacktest,
  onSaveNewVersion,
  isExecuting,
  externalParamsToApply,
}) => {
  const currentVersion = selectedStrategy?.latest_version;
  const initialParams = currentVersion?.parameters || {
    rsi_period: 14,
    oversold: 30.0,
    overbought: 70.0,
    risk_reward_ratio: 2.0,
    risk_per_trade_pct: 0.01,
    sl_atr_mult: 1.5,
    max_bars_held: 48,
  };

  const [params, setParams] = useState<Record<string, any>>(initialParams);
  const [slippageBps, setSlippageBps] = useState<number>(1.0);
  const [commission, setCommission] = useState<number>(1.0);
  const [spreadPips, setSpreadPips] = useState<number>(0.2);
  const [initialCapital, setInitialCapital] = useState<number>(10000);
  const [symbol, setSymbol] = useState<string>("XAUUSD");
  const [timeframe, setTimeframe] = useState<string>("1H");
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  React.useEffect(() => {
    if (externalParamsToApply) {
      setParams((prev) => ({ ...prev, ...externalParamsToApply }));
    }
  }, [externalParamsToApply]);

  React.useEffect(() => {
    if (currentVersion?.parameters) {
      setParams(currentVersion.parameters);
    }
  }, [currentVersion]);

  const handleParamChange = (key: string, value: any) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleLaunch = () => {
    if (!currentVersion) return;
    onLaunchBacktest({
      versionId: currentVersion.id,
      symbol,
      timeframe,
      initialCapital,
      slippageBps,
      commission,
      spreadPips,
      riskPct: params.risk_per_trade_pct || 0.01,
    });
  };

  const handleSaveVersion = async () => {
    try {
      await onSaveNewVersion(params);
      setSaveSuccess("Saved immutable strategy version snapshot!");
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (e: any) {
      alert(`Failed to save version: ${e.message}`);
    }
  };

  const isDivergence = selectedStrategy?.strategy_type === "divergence";

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 flex flex-col space-y-4">
      {/* Strategy Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-accent" />
          <span className="text-xs font-mono font-bold text-white tracking-wider">
            STRATEGY & PARAMETER LAB
          </span>
        </div>

        {/* Strategy Selector */}
        <div className="flex items-center space-x-2">
          <select
            value={selectedStrategy?.id || ""}
            onChange={(e) => {
              const s = strategies.find((st) => st.id === e.target.value);
              if (s) onSelectStrategy(s);
            }}
            className="bg-[#0f1422] border border-surfaceBorder rounded px-2.5 py-1 text-xs font-mono text-white focus:outline-none focus:border-accent"
          >
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.strategy_type.toUpperCase()})
              </option>
            ))}
          </select>

          {currentVersion && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
              v{currentVersion.version_number} • {currentVersion.code_hash.slice(0, 8)}
            </span>
          )}
        </div>
      </div>

      {saveSuccess && (
        <div className="flex items-center text-xs text-emerald-400 font-mono bg-emerald-950/60 border border-emerald-800 px-3 py-1.5 rounded">
          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
          {saveSuccess}
        </div>
      )}

      {/* Grid of Strategy Parameters */}
      <div>
        <div className="text-[11px] font-mono text-gray-400 mb-2 font-semibold">
          ALGORITHMIC PARAMETERS ({selectedStrategy?.strategy_type.toUpperCase()})
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div>
            <label className="text-gray-400 block mb-1">RSI Period</label>
            <input
              type="number"
              value={params.rsi_period ?? 14}
              onChange={(e) => handleParamChange("rsi_period", parseInt(e.target.value) || 14)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>

          <div>
            <label className="text-gray-400 block mb-1">Oversold Level</label>
            <input
              type="number"
              value={params.oversold ?? params.oversold_threshold ?? 30}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || 30;
                handleParamChange(isDivergence ? "oversold_threshold" : "oversold", val);
              }}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>

          <div>
            <label className="text-gray-400 block mb-1">Overbought Level</label>
            <input
              type="number"
              value={params.overbought ?? params.overbought_threshold ?? 70}
              onChange={(e) => {
                const val = parseFloat(e.target.value) || 70;
                handleParamChange(isDivergence ? "overbought_threshold" : "overbought", val);
              }}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>

          <div>
            <label className="text-gray-400 block mb-1">Risk:Reward Ratio</label>
            <input
              type="number"
              step="0.1"
              value={params.risk_reward_ratio ?? 2.0}
              onChange={(e) => handleParamChange("risk_reward_ratio", parseFloat(e.target.value) || 2.0)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>

          {isDivergence ? (
            <>
              <div>
                <label className="text-gray-400 block mb-1">Swing Window (Bars)</label>
                <input
                  type="number"
                  value={params.swing_window ?? 5}
                  onChange={(e) => handleParamChange("swing_window", parseInt(e.target.value) || 5)}
                  className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
                />
              </div>
              <div>
                <label className="text-gray-400 block mb-1">Entry Mode</label>
                <select
                  value={params.entry_mode ?? "early_candlestick"}
                  onChange={(e) => handleParamChange("entry_mode", e.target.value)}
                  className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2 py-1.5 text-white"
                >
                  <option value="early_candlestick">Early Candlestick</option>
                  <option value="neckline_breakout">Neckline Breakout</option>
                </select>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="text-gray-400 block mb-1">Stop Loss (ATR Mult)</label>
                <input
                  type="number"
                  step="0.1"
                  value={params.sl_atr_mult ?? 1.5}
                  onChange={(e) => handleParamChange("sl_atr_mult", parseFloat(e.target.value) || 1.5)}
                  className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
                />
              </div>
              <div>
                <label className="text-gray-400 block mb-1">Max Bars Held</label>
                <input
                  type="number"
                  value={params.max_bars_held ?? 48}
                  onChange={(e) => handleParamChange("max_bars_held", parseInt(e.target.value) || 48)}
                  className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Execution Cost Assumptions */}
      <div className="pt-2 border-t border-surfaceBorder">
        <div className="text-[11px] font-mono text-gray-400 mb-2 font-semibold">
          REALISTIC EXECUTION & COST MODELING
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div>
            <label className="text-gray-400 block mb-1">Slippage (Bps)</label>
            <input
              type="number"
              step="0.5"
              value={slippageBps}
              onChange={(e) => setSlippageBps(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">Commission ($/order)</label>
            <input
              type="number"
              step="0.5"
              value={commission}
              onChange={(e) => setCommission(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">Spread (Pips)</label>
            <input
              type="number"
              step="0.1"
              value={spreadPips}
              onChange={(e) => setSpreadPips(parseFloat(e.target.value) || 0)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">Risk % Per Trade</label>
            <input
              type="number"
              step="0.005"
              value={params.risk_per_trade_pct ?? 0.01}
              onChange={(e) => handleParamChange("risk_per_trade_pct", parseFloat(e.target.value) || 0.01)}
              className="w-full bg-[#0d111a] border border-surfaceBorder rounded px-2.5 py-1.5 text-white"
            />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-2 border-t border-surfaceBorder">
        <button
          onClick={handleSaveVersion}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#1e2433] hover:bg-[#283247] text-gray-200 text-xs font-mono transition-colors"
        >
          <Save className="w-3.5 h-3.5" />
          <span>Save Version Snapshot</span>
        </button>

        <button
          onClick={handleLaunch}
          disabled={isExecuting}
          className={`flex items-center space-x-2 px-4 py-2 rounded text-xs font-mono font-bold text-white transition-all ${
            isExecuting
              ? "bg-blue-800 cursor-not-allowed opacity-75"
              : "bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-900/30"
          }`}
        >
          <Play className={`w-3.5 h-3.5 ${isExecuting ? "animate-spin" : ""}`} />
          <span>{isExecuting ? "Running Async Engine..." : "Launch Backtest Run"}</span>
        </button>
      </div>
    </div>
  );
};
