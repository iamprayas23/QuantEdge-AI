"use client";

import React, { useState, useEffect } from "react";
import { api, setAuthToken } from "@/lib/api";
import {
  Strategy,
  BacktestRun,
  Tearsheet,
  OHLCVBar,
  StrategySpecOutput,
  BacktestCritiqueOutput,
} from "@/types";
import { MetricsGrid } from "@/components/MetricsGrid";
import { CandlestickChart } from "@/components/CandlestickChart";
import { EquityChart } from "@/components/EquityChart";
import { TradeBlotter } from "@/components/TradeBlotter";
import { StrategyLab } from "@/components/StrategyLab";
import { AICritiquePanel } from "@/components/AICritiquePanel";
import { CommitteePanel } from "@/components/CommitteePanel";
import { CatalystRegimeFeed } from "@/components/CatalystRegimeFeed";
import { RiskGuardrailsPanel } from "@/components/RiskGuardrailsPanel";
import { WalkForwardLab } from "@/components/WalkForwardLab";
import { CashflowPlannerPanel } from "@/components/CashflowPlannerPanel";
import {
  Activity,
  ShieldCheck,
  Database,
  Terminal,
  RefreshCw,
  Users,
  RotateCcw,
  Calendar,
  Wallet,
  Sliders,
} from "lucide-react";

export default function QuantEdgeApp() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [activeTearsheet, setActiveTearsheet] = useState<Tearsheet | null>(null);
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [apiConnected, setApiConnected] = useState<boolean>(false);
  const [userEmail, setUserEmail] = useState<string>("quant@edge.io");
  const [workspaceName, setWorkspaceName] = useState<string>("Alpha Core Workspace");
  const [appliedParams, setAppliedParams] = useState<Record<string, any> | null>(null);
  const [activePillarTab, setActivePillarTab] = useState<"committee" | "walk_forward" | "guardrails" | "catalysts" | "planner">("committee");

  // Initialize session & load initial data
  useEffect(() => {
    const initSession = async () => {
      try {
        // Authenticate or register demo quant account
        const authRes = await api.login({ email: "trader_dev@quantedge.io", password: "DevPassword123!" })
          .catch(async () => {
            return await api.register({
              email: "trader_dev@quantedge.io",
              password: "DevPassword123!",
              workspace_name: "Alpha Core Workspace",
            });
          });

        setAuthToken(authRes.access_token, authRes.workspace_id);
        setApiConnected(true);

        // Fetch user info
        const me = await api.getMe();
        setUserEmail(me.email);
        if (me.workspaces && me.workspaces.length > 0) {
          setWorkspaceName(me.workspaces[0].name);
        }

        // Fetch strategies
        let strats = await api.listStrategies();
        if (strats.length === 0) {
          // Create initial baseline strategies
          const s1 = await api.createStrategy({
            name: "Gold RSI Mean Reversion",
            description: "Institutional 1H mean-reversion with volatility stops",
            strategy_type: "rsi",
            initial_parameters: {
              rsi_period: 14,
              oversold: 30.0,
              overbought: 70.0,
              risk_per_trade_pct: 0.01,
              risk_reward_ratio: 2.0,
              sl_atr_mult: 1.5,
              max_bars_held: 48,
            },
          });
          const s2 = await api.createStrategy({
            name: "XAUUSD Divergence Causal",
            description: "Strictly causal regular divergence with ATR risk management",
            strategy_type: "divergence",
            initial_parameters: {
              rsi_period: 14,
              swing_window: 5,
              entry_mode: "early_candlestick",
              risk_per_trade_pct: 0.01,
              risk_reward_ratio: 2.0,
              sl_buffer_atr: 0.2,
              oversold_threshold: 35.0,
              overbought_threshold: 65.0,
              max_bars_held: 72,
            },
          });
          strats = [s1, s2];
        }

        setStrategies(strats);
        setSelectedStrategy(strats[0]);

        // Load OHLCV bars for gold
        const barData = await api.getBars("XAUUSD", "1H", 300);
        setBars(barData);

        // Check if there are past runs to display tearsheet
        const runs = await api.listRuns();
        const completed = runs.find((r) => r.status === "COMPLETED");
        if (completed) {
          const ts = await api.getTearsheet(completed.id);
          setActiveTearsheet(ts);
          if (ts.run?.symbol && ts.run?.timeframe && (ts.run.symbol !== "XAUUSD" || ts.run.timeframe !== "1H")) {
            const runBars = await api.getBars(ts.run.symbol, ts.run.timeframe, 300);
            if (runBars && runBars.length > 0) {
              setBars(runBars);
            }
          }
        }
      } catch (err) {
        console.warn("API initialization note:", err);
      }
    };

    initSession();
  }, []);

  // Launch async backtest and poll for status
  const handleLaunchBacktest = async (launchConfig: {
    versionId: string;
    symbol: string;
    timeframe: string;
    initialCapital: number;
    slippageBps: number;
    commission: number;
    spreadPips: number;
    riskPct: number;
  }) => {
    setIsExecuting(true);
    try {
      const job = await api.launchBacktest({
        strategy_version_id: launchConfig.versionId,
        symbol: launchConfig.symbol,
        timeframe: launchConfig.timeframe,
        initial_capital: launchConfig.initialCapital,
        slippage_bps: launchConfig.slippageBps,
        commission_per_trade: launchConfig.commission,
        spread_pips: launchConfig.spreadPips,
        risk_per_trade_pct: launchConfig.riskPct,
      });

      // Poll status every 600ms
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await api.getRunStatus(job.job_id);
          if (statusRes.status === "COMPLETED") {
            clearInterval(pollInterval);
            setIsExecuting(false);
            const tearsheet = await api.getTearsheet(job.job_id);
            setActiveTearsheet(tearsheet);
            try {
              const runBars = await api.getBars(launchConfig.symbol, launchConfig.timeframe, 300);
              if (runBars && runBars.length > 0) {
                setBars(runBars);
              }
            } catch (barErr) {
              console.warn("Failed to update chart bars after run:", barErr);
            }
          } else if (statusRes.status === "FAILED") {
            clearInterval(pollInterval);
            setIsExecuting(false);
            alert(`Backtest execution failed: ${statusRes.error_message}`);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setIsExecuting(false);
        }
      }, 600);
    } catch (err: any) {
      setIsExecuting(false);
      alert(`Launch error: ${err.message}`);
    }
  };

  // Save new immutable version
  const handleSaveVersion = async (newParams: Record<string, any>) => {
    if (!selectedStrategy) return;
    const v = await api.createVersion(selectedStrategy.id, newParams);
    // Refresh strategy versions
    const updatedStrats = await api.listStrategies();
    setStrategies(updatedStrats);
    const updatedSelected = updatedStrats.find((s) => s.id === selectedStrategy.id);
    if (updatedSelected) setSelectedStrategy(updatedSelected);
  };

  // Grounded AI hypothesis parsing
  const handleParseHypothesis = async (prompt: string): Promise<StrategySpecOutput> => {
    return await api.parseHypothesis(prompt);
  };

  // Grounded AI critique
  const handleCritiqueRun = async (): Promise<BacktestCritiqueOutput> => {
    if (!activeTearsheet?.run?.id) {
      throw new Error("No completed backtest run selected to critique");
    }
    return await api.critiqueBacktest(activeTearsheet.run.id);
  };

  // Multi-Agent Committee
  const handleConveneCommittee = async (params: {
    symbol: string;
    timeframe: string;
    strategyVersionId?: string;
    backtestRunId?: string;
  }) => {
    return await api.conveneCommittee({
      symbol: params.symbol,
      timeframe: params.timeframe,
      strategy_version_id: params.strategyVersionId,
      backtest_run_id: params.backtestRunId,
      limit_bars: 300,
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0d14] text-[#e2e8f0]">
      {/* Top Institutional Header */}
      <header className="border-b border-surfaceBorder bg-[#0d111a] px-4 py-2.5 flex items-center justify-between sticky top-0 z-30 shadow-md">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-accent rotate-45"></span>
            <span className="font-mono font-extrabold text-sm tracking-wider text-white">
              QUANTEDGE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surfaceBorder text-gray-400">
              v0.2.0
            </span>
          </div>

          <div className="hidden md:flex items-center space-x-2 border-l border-surfaceBorder pl-3 text-xs font-mono text-gray-400">
            <Database className="w-3.5 h-3.5 text-accent" />
            <span>Feed: XAUUSD (1H UTC)</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#131826] border border-surfaceBorder">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-gray-300">{workspaceName}</span>
          </div>

          <div className="hidden sm:flex items-center space-x-1 text-gray-400">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Zero-Lookahead Mode Active</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 space-y-4 max-w-[1600px] w-full mx-auto">
        {/* KPI Summary Banner */}
        <MetricsGrid
          metrics={activeTearsheet?.metrics || {}}
          initialCapital={activeTearsheet?.run?.initial_capital || 10000}
        />

        {/* Charts & Tearsheet Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left 2 Cols: Candlestick & Equity Curves */}
          <div className="lg:col-span-2 space-y-4">
            <CandlestickChart
              bars={bars}
              trades={activeTearsheet?.recent_trades || []}
              symbol="XAUUSD"
              timeframe="1H"
            />
            <EquityChart
              equityCurve={activeTearsheet?.equity_curve || []}
              initialCapital={activeTearsheet?.run?.initial_capital || 10000}
            />
          </div>

          {/* Right Col: Strategy Lab & Parameter Controls */}
          <div className="space-y-4">
            <StrategyLab
              strategies={strategies}
              selectedStrategy={selectedStrategy}
              onSelectStrategy={(s) => setSelectedStrategy(s)}
              onLaunchBacktest={handleLaunchBacktest}
              onSaveNewVersion={handleSaveVersion}
              isExecuting={isExecuting}
              externalParamsToApply={appliedParams}
            />

            <AICritiquePanel
              onApplySpec={(p) => setAppliedParams(p)}
              onParseHypothesis={handleParseHypothesis}
              onCritiqueRun={handleCritiqueRun}
              hasCompletedRun={!!activeTearsheet?.run?.id}
            />
          </div>
        </div>

        {/* Institutional 5 Pillars & Committee Navigation Tabs */}
        <div className="bg-[#0c1018] border border-surfaceBorder rounded-lg p-1.5 flex flex-wrap items-center gap-1.5 font-mono text-xs">
          <button
            onClick={() => setActivePillarTab("committee")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activePillarTab === "committee"
                ? "bg-cyan-600 text-white font-bold shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-surface"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Multi-Agent Committee</span>
          </button>

          <button
            onClick={() => setActivePillarTab("walk_forward")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activePillarTab === "walk_forward"
                ? "bg-purple-600 text-white font-bold shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-surface"
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Pillar 3: Walk-Forward & Stress Lab</span>
          </button>

          <button
            onClick={() => setActivePillarTab("guardrails")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activePillarTab === "guardrails"
                ? "bg-emerald-600 text-white font-bold shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-surface"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Pillars 2 & 4: Guardrails & Risk Monitor</span>
          </button>

          <button
            onClick={() => setActivePillarTab("catalysts")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activePillarTab === "catalysts"
                ? "bg-blue-600 text-white font-bold shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-surface"
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Pillar 1: Catalysts & Macro Feed</span>
          </button>

          <button
            onClick={() => setActivePillarTab("planner")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activePillarTab === "planner"
                ? "bg-amber-600 text-white font-bold shadow-sm"
                : "text-gray-400 hover:text-white hover:bg-surface"
            }`}
          >
            <Wallet className="w-3.5 h-3.5" />
            <span>Pillar 5: Capital & Tax Planner</span>
          </button>
        </div>

        {/* Dynamic Pillar Workspace Rendering */}
        {activePillarTab === "committee" && (
          <CommitteePanel
            onApplyProposal={(p) => setAppliedParams(p)}
            onConveneCommittee={handleConveneCommittee}
            selectedStrategy={selectedStrategy}
            activeRun={activeTearsheet?.run || null}
          />
        )}

        {activePillarTab === "walk_forward" && (
          <WalkForwardLab selectedStrategy={selectedStrategy} />
        )}

        {activePillarTab === "guardrails" && (
          <RiskGuardrailsPanel activeRun={activeTearsheet?.run || null} />
        )}

        {activePillarTab === "catalysts" && (
          <CatalystRegimeFeed />
        )}

        {activePillarTab === "planner" && (
          <CashflowPlannerPanel />
        )}

        {/* Bottom: Trade Blotter */}
        <TradeBlotter trades={activeTearsheet?.recent_trades || []} />
      </main>

      {/* Footer */}
      <footer className="border-t border-surfaceBorder bg-[#0c1018] px-4 py-2 text-center text-xs font-mono text-gray-500">
        QuantEdge Institutional Quant Architecture • Deterministic Causal Engine • Pydantic AI Grounding Layer
      </footer>
    </div>
  );
}
