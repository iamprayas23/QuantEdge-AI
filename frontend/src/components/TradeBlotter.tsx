import React, { useState } from "react";
import { TradeItem } from "@/types";
import { ArrowUpRight, ArrowDownRight, Filter } from "lucide-react";

interface TradeBlotterProps {
  trades: TradeItem[];
}

export const TradeBlotter: React.FC<TradeBlotterProps> = ({ trades }) => {
  const [filter, setFilter] = useState<"all" | "long" | "short" | "win" | "loss">("all");

  const filteredTrades = trades.filter((t) => {
    if (filter === "long") return t.side === "long";
    if (filter === "short") return t.side === "short";
    if (filter === "win") return t.pnl > 0;
    if (filter === "loss") return t.pnl < 0;
    return true;
  });

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg overflow-hidden flex flex-col">
      {/* Header and Filter Buttons */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 border-b border-surfaceBorder bg-[#0c1018]">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono font-bold text-white tracking-wider">
            TRADE BLOTTER
          </span>
          <span className="text-xs text-gray-400 font-mono">
            ({filteredTrades.length} of {trades.length} trades)
          </span>
        </div>

        <div className="flex items-center space-x-1.5 text-xs font-mono">
          <button
            onClick={() => setFilter("all")}
            className={`px-2 py-0.5 rounded ${
              filter === "all" ? "bg-blue-600 text-white" : "bg-surfaceBorder text-gray-400 hover:text-white"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter("long")}
            className={`px-2 py-0.5 rounded ${
              filter === "long" ? "bg-emerald-600 text-white" : "bg-surfaceBorder text-gray-400 hover:text-white"
            }`}
          >
            Longs
          </button>
          <button
            onClick={() => setFilter("short")}
            className={`px-2 py-0.5 rounded ${
              filter === "short" ? "bg-rose-600 text-white" : "bg-surfaceBorder text-gray-400 hover:text-white"
            }`}
          >
            Shorts
          </button>
          <button
            onClick={() => setFilter("win")}
            className={`px-2 py-0.5 rounded ${
              filter === "win" ? "bg-emerald-700 text-white" : "bg-surfaceBorder text-gray-400 hover:text-white"
            }`}
          >
            Wins
          </button>
          <button
            onClick={() => setFilter("loss")}
            className={`px-2 py-0.5 rounded ${
              filter === "loss" ? "bg-rose-700 text-white" : "bg-surfaceBorder text-gray-400 hover:text-white"
            }`}
          >
            Losses
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[320px] overflow-y-auto">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead className="sticky top-0 bg-[#0f1422] text-gray-400 border-b border-surfaceBorder z-10">
            <tr>
              <th className="py-2 px-3">#</th>
              <th className="py-2 px-3">Side</th>
              <th className="py-2 px-3">Entry Time</th>
              <th className="py-2 px-3">Exit Time</th>
              <th className="py-2 px-3 text-right">Entry</th>
              <th className="py-2 px-3 text-right">Exit</th>
              <th className="py-2 px-3 text-right">Lots</th>
              <th className="py-2 px-3 text-right">Net PnL</th>
              <th className="py-2 px-3 text-right">Return</th>
              <th className="py-2 px-3">Exit Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surfaceBorder">
            {filteredTrades.map((t) => {
              const isWin = t.pnl >= 0;
              return (
                <tr key={t.trade_number} className="hover:bg-surfaceHover transition-colors">
                  <td className="py-1.5 px-3 text-gray-400">{t.trade_number}</td>
                  <td className="py-1.5 px-3">
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        t.side === "long" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-rose-950 text-rose-400 border border-rose-800"
                      }`}
                    >
                      {t.side === "long" ? (
                        <>
                          <ArrowUpRight className="w-3 h-3 mr-0.5" /> LONG
                        </>
                      ) : (
                        <>
                          <ArrowDownRight className="w-3 h-3 mr-0.5" /> SHORT
                        </>
                      )}
                    </span>
                  </td>
                  <td className="py-1.5 px-3 text-gray-300">{t.entry_ts.slice(0, 16).replace("T", " ")}</td>
                  <td className="py-1.5 px-3 text-gray-300">{t.exit_ts.slice(0, 16).replace("T", " ")}</td>
                  <td className="py-1.5 px-3 text-right font-medium text-white">{t.entry_price.toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right font-medium text-white">{t.exit_price.toFixed(2)}</td>
                  <td className="py-1.5 px-3 text-right text-gray-300">{t.size.toFixed(2)}</td>
                  <td className={`py-1.5 px-3 text-right font-bold ${isWin ? "text-bull" : "text-bear"}`}>
                    {isWin ? "+" : ""}${t.pnl.toFixed(2)}
                  </td>
                  <td className={`py-1.5 px-3 text-right ${isWin ? "text-bull" : "text-bear"}`}>
                    {isWin ? "+" : ""}{t.return_pct.toFixed(2)}%
                  </td>
                  <td className="py-1.5 px-3 text-gray-400">
                    <span className="capitalize">{t.exit_reason.replace("_", " ")}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
