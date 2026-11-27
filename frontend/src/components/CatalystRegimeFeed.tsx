"use client";

import React, { useState, useEffect } from "react";
import { MarketCatalystEvent, CatalystBriefOutput } from "@/types";
import { api } from "@/lib/api";
import {
  Calendar,
  Sparkles,
  Zap,
  ShieldAlert,
  TrendingUp,
  TrendingDown,
  Clock,
  Activity,
  AlertCircle,
} from "lucide-react";

export const CatalystRegimeFeed: React.FC = () => {
  const [catalysts, setCatalysts] = useState<MarketCatalystEvent[]>([]);
  const [brief, setBrief] = useState<CatalystBriefOutput | null>(null);
  const [loadingBrief, setLoadingBrief] = useState<boolean>(false);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCatalysts();
  }, []);

  const loadCatalysts = async () => {
    setLoadingEvents(true);
    try {
      const data = await api.getCatalysts("XAUUSD", 30);
      setCatalysts(data);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoadingEvents(false);
    }
  };

  const handleGenerateBrief = async () => {
    setLoadingBrief(true);
    setError(null);
    try {
      const res = await api.getCatalystBrief("XAUUSD", "1H");
      setBrief(res);
    } catch (e: any) {
      setError(e.message || "Failed to generate catalyst brief");
    } finally {
      setLoadingBrief(false);
    }
  };

  const getImpactBadge = (impact: string) => {
    if (impact === "HIGH") {
      return (
        <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-rose-950 text-rose-300 border border-rose-800">
          HIGH
        </span>
      );
    }
    if (impact === "MEDIUM") {
      return (
        <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-amber-950 text-amber-300 border border-amber-800">
          MED
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-gray-800 text-gray-300">
        LOW
      </span>
    );
  };

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4 space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-surfaceBorder gap-2">
        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold text-white tracking-wider">
            PILLAR 1: MARKET CATALYSTS & REGIME CONTEXT
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
            Macro & Volatility Alignment
          </span>
        </div>

        <button
          onClick={handleGenerateBrief}
          disabled={loadingBrief}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded text-xs font-bold transition shadow-sm"
        >
          {loadingBrief ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Analyzing Shocks...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5" />
              <span>Generate Grounded Brief</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Grounded Brief Card */}
      {brief && (
        <div className="p-3.5 bg-[#0b0e17] border border-cyan-900/60 rounded-lg space-y-3">
          <div className="flex items-center justify-between border-b border-surfaceBorder/60 pb-2">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-white uppercase">
                Institutional Macro Brief • {brief.symbol}
              </span>
            </div>
            <span className="text-[10px] text-gray-400">
              Regime: <span className="text-cyan-300 font-bold">{brief.current_regime}</span> (Vol: {brief.realized_vol_pct}%)
            </span>
          </div>

          <p className="text-xs text-gray-200 leading-relaxed">
            {brief.executive_brief}
          </p>

          {/* Impact Multipliers */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#121829] p-2.5 rounded border border-surfaceBorder/50 text-[11px]">
            <div>
              <span className="text-gray-400 block text-[10px]">Range Multiplier</span>
              <span className="text-white font-bold">{brief.catalyst_impact_metrics.range_multiplier}x Normal</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Vol Spike Ratio</span>
              <span className="text-purple-300 font-bold">{brief.catalyst_impact_metrics.vol_spike_ratio}x Baseline</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Catalyst Window Vol</span>
              <span className="text-amber-300 font-bold">{brief.catalyst_impact_metrics.catalyst_realized_vol}%</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[10px]">Normal Realized Vol</span>
              <span className="text-gray-300 font-bold">{brief.catalyst_impact_metrics.normal_realized_vol}%</span>
            </div>
          </div>

          <div className="text-[11px] text-amber-300/90 bg-amber-950/40 p-2 rounded border border-amber-900/60 flex items-start space-x-1.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <span>{brief.risk_advisory}</span>
          </div>
        </div>
      )}

      {/* Catalyst Timeline Table */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-gray-300 flex items-center justify-between">
          <span>SCHEDULED MACRO & RATE EVENTS</span>
          <span className="text-[10px] text-gray-500">{catalysts.length} Historical & Active Events</span>
        </div>

        <div className="overflow-x-auto border border-surfaceBorder rounded-lg">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0f1422] text-gray-400 border-b border-surfaceBorder text-[10px] uppercase">
              <tr>
                <th className="p-2">Date (UTC)</th>
                <th className="p-2">Asset</th>
                <th className="p-2">Event Headline</th>
                <th className="p-2">Category</th>
                <th className="p-2">Impact</th>
                <th className="p-2">Bias</th>
                <th className="p-2 text-right">Actual / Forecast</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surfaceBorder/40">
              {catalysts.map((c, i) => (
                <tr key={c.id || i} className="hover:bg-surfaceHover/50 transition">
                  <td className="p-2 text-[11px] text-gray-400 whitespace-nowrap">
                    {new Date(c.timestamp_utc).toLocaleDateString()} {new Date(c.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="p-2 font-bold text-white">{c.symbol}</td>
                  <td className="p-2 text-gray-200">{c.title}</td>
                  <td className="p-2">
                    <span className="px-1.5 py-0.5 rounded bg-gray-800 text-[10px] text-gray-300 uppercase">
                      {c.category}
                    </span>
                  </td>
                  <td className="p-2">{getImpactBadge(c.impact)}</td>
                  <td className="p-2">
                    <span className={`text-[10px] font-bold ${
                      c.sentiment === "BULLISH" || c.sentiment === "DOVISH" ? "text-emerald-400" :
                      c.sentiment === "BEARISH" || c.sentiment === "HAWKISH" ? "text-rose-400" : "text-gray-400"
                    }`}>
                      {c.sentiment}
                    </span>
                  </td>
                  <td className="p-2 text-right text-[11px] text-gray-300 font-mono">
                    {c.actual_value || "--"} <span className="text-gray-500">/ {c.forecast_value || "--"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
