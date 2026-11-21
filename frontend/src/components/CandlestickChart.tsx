import React, { useEffect, useRef } from "react";
import { OHLCVBar, TradeItem } from "@/types";

interface CandlestickChartProps {
  bars: OHLCVBar[];
  trades?: TradeItem[];
  symbol?: string;
  timeframe?: string;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  bars,
  trades = [],
  symbol = "XAUUSD",
  timeframe = "1H",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    let chart: any = null;
    let isDisposed = false;

    const initChart = async () => {
      try {
        const { createChart, ColorType } = await import("lightweight-charts");

        if (isDisposed || !containerRef.current) return;
        containerRef.current.innerHTML = "";

        chart = createChart(containerRef.current, {
          width: containerRef.current.clientWidth,
          height: 380,
          layout: {
            background: { type: ColorType.Solid, color: "#0d111a" },
            textColor: "#94a3b8",
          },
          grid: {
            vertLines: { color: "#182030" },
            horzLines: { color: "#182030" },
          },
          crosshair: {
            mode: 1,
          },
          timeScale: {
            borderColor: "#1e293b",
            timeVisible: true,
            secondsVisible: false,
          },
        });

        chartInstanceRef.current = chart;

        const candleSeries = chart.addCandlestickSeries({
          upColor: "#10b981",
          downColor: "#ef4444",
          borderVisible: false,
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
        });

        // Format bars for lightweight charts
        const formattedBars = bars.map((b) => ({
          time: b.time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }));

        candleSeries.setData(formattedBars);

        // Add markers for trades
        if (trades.length > 0) {
          const markers: any[] = [];
          trades.forEach((t) => {
            const entryTime = Math.floor(new Date(t.entry_ts).getTime() / 1000);
            const exitTime = Math.floor(new Date(t.exit_ts).getTime() / 1000);

            if (t.side === "long") {
              markers.push({
                time: entryTime,
                position: "belowBar",
                color: "#10b981",
                shape: "arrowUp",
                text: `BUY @ ${t.entry_price.toFixed(1)}`,
              });
            } else {
              markers.push({
                time: entryTime,
                position: "aboveBar",
                color: "#ef4444",
                shape: "arrowDown",
                text: `SELL @ ${t.entry_price.toFixed(1)}`,
              });
            }

            markers.push({
              time: exitTime,
              position: t.side === "long" ? "aboveBar" : "belowBar",
              color: t.pnl >= 0 ? "#10b981" : "#ef4444",
              shape: "circle",
              text: `${t.exit_reason} (${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(0)})`,
            });
          });

          // Sort markers chronologically
          markers.sort((a, b) => a.time - b.time);
          candleSeries.setMarkers(markers);
        }

        chart.timeScale().fitContent();

        const handleResize = () => {
          if (containerRef.current && chart) {
            chart.applyOptions({ width: containerRef.current.clientWidth });
          }
        };

        window.addEventListener("resize", handleResize);

        return () => {
          window.removeEventListener("resize", handleResize);
        };
      } catch (err) {
        console.warn("Lightweight charts failed to load, rendering canvas fallback:", err);
      }
    };

    initChart();

    return () => {
      isDisposed = true;
      if (chart) {
        chart.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [bars, trades]);

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-surfaceBorder bg-[#0c1018]">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono font-bold text-white tracking-wider">{symbol}</span>
          <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
            {timeframe}
          </span>
          <span className="text-xs text-gray-400 font-mono">
            ({bars.length} closed bars)
          </span>
        </div>
        <div className="flex items-center space-x-3 text-xs font-mono text-gray-400">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-bull mr-1"></span> Buy Entries
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-bear mr-1"></span> Sell Entries
          </span>
        </div>
      </div>
      <div ref={containerRef} className="w-full h-[380px]" />
    </div>
  );
};
