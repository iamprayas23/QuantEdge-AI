import React from "react";
import { TrendingUp, TrendingDown, ShieldAlert, Award, Activity, DollarSign, Percent, BarChart2 } from "lucide-react";

interface MetricsGridProps {
  metrics: Record<string, any>;
  initialCapital?: number;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({ metrics, initialCapital = 10000 }) => {
  const totalReturn = metrics.total_return ?? 0;
  const sharpe = metrics.sharpe_ratio ?? 0;
  const sortino = metrics.sortino_ratio ?? 0;
  const maxDd = metrics.max_drawdown ?? 0;
  const winRate = metrics.win_rate ?? 0;
  const profitFactor = metrics.profit_factor ?? 0;
  const totalTrades = metrics.total_trades ?? 0;
  const winningTrades = metrics.winning_trades ?? 0;
  const losingTrades = metrics.losing_trades ?? 0;
  const finalEquity = metrics.final_equity ?? initialCapital;
  const totalCost = (metrics.total_commission ?? 0) + (metrics.total_slippage ?? 0);

  const isProfitable = totalReturn >= 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
      {/* Final Equity / Return */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3 relative overflow-hidden">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>PORTFOLIO EQUITY</span>
          {isProfitable ? <TrendingUp className="w-3.5 h-3.5 text-bull" /> : <TrendingDown className="w-3.5 h-3.5 text-bear" />}
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-white">
          ${finalEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div className={`text-xs font-mono font-medium mt-0.5 ${isProfitable ? "text-bull" : "text-bear"}`}>
          {isProfitable ? "+" : ""}{totalReturn.toFixed(2)}%
        </div>
      </div>

      {/* Sharpe Ratio */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>SHARPE RATIO</span>
          <Award className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-white">
          {sharpe.toFixed(2)}
        </div>
        <div className="text-xs font-mono text-gray-400 mt-0.5">
          {sharpe >= 1.5 ? (
            <span className="text-emerald-400">Excellent</span>
          ) : sharpe >= 1.0 ? (
            <span className="text-blue-400">Acceptable</span>
          ) : sharpe > 0 ? (
            <span className="text-yellow-400">Sub-optimal</span>
          ) : (
            <span className="text-red-400">Negative Alpha</span>
          )}
        </div>
      </div>

      {/* Sortino Ratio */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>SORTINO RATIO</span>
          <Activity className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-white">
          {sortino.toFixed(2)}
        </div>
        <div className="text-xs font-mono text-gray-400 mt-0.5">
          Downside Risk Adj.
        </div>
      </div>

      {/* Max Drawdown */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>MAX DRAWDOWN</span>
          <ShieldAlert className="w-3.5 h-3.5 text-bear" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-bear">
          -{maxDd.toFixed(2)}%
        </div>
        <div className="text-xs font-mono text-gray-400 mt-0.5">
          {maxDd > 20 ? "High tail-risk" : "Within bounds"}
        </div>
      </div>

      {/* Win Rate */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>WIN RATE</span>
          <Percent className="w-3.5 h-3.5 text-gold" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-white">
          {winRate.toFixed(1)}%
        </div>
        <div className="text-xs font-mono text-gray-400 mt-0.5">
          {winningTrades}W / {losingTrades}L
        </div>
      </div>

      {/* Profit Factor & Trades */}
      <div className="bg-surface border border-surfaceBorder rounded-lg p-3">
        <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>PROFIT FACTOR</span>
          <BarChart2 className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-xl font-bold font-mono mt-1 text-white">
          {profitFactor >= 999 ? "∞" : profitFactor.toFixed(2)}
        </div>
        <div className="text-xs font-mono text-gray-400 mt-0.5">
          {totalTrades} Total Trades
        </div>
      </div>
    </div>
  );
};
