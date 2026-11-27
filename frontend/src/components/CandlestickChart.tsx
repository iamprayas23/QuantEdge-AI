import React, { useEffect, useRef, useMemo, useState } from "react";
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
  const [renderedBarCount, setRenderedBarCount] = useState<number>(0);

  // 1. Sanitize, validate, deduplicate, and sort bars chronologically
  const sanitizedBars = useMemo(() => {
    if (!bars || bars.length === 0) return [];

    const valid = bars
      .filter(
        (b) =>
          b &&
          typeof b.time === "number" &&
          !isNaN(b.time) &&
          b.time > 0 &&
          typeof b.open === "number" &&
          !isNaN(b.open) &&
          typeof b.high === "number" &&
          !isNaN(b.high) &&
          typeof b.low === "number" &&
          !isNaN(b.low) &&
          typeof b.close === "number" &&
          !isNaN(b.close)
      )
      .map((b) => ({
        time: b.time as any,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    // Strictly unique ascending timestamps required by lightweight-charts
    const deduped: typeof valid = [];
    for (let i = 0; i < valid.length; i++) {
      const curr = valid[i];
      if (
        deduped.length === 0 ||
        (deduped[deduped.length - 1].time as number) !== (curr.time as number)
      ) {
        deduped.push(curr);
      } else {
        deduped[deduped.length - 1] = curr;
      }
    }
    return deduped;
  }, [bars]);

  useEffect(() => {
    setRenderedBarCount(sanitizedBars.length);
  }, [sanitizedBars.length]);

  useEffect(() => {
    if (!containerRef.current || sanitizedBars.length === 0) return;

    let chart: any = null;
    let isDisposed = false;
    let resizeObserver: ResizeObserver | null = null;

    const initChart = async () => {
      try {
        const lc = await import("lightweight-charts");
        const { createChart, ColorType } = lc;
        const CandlestickSeries = (lc as any).CandlestickSeries;
        const createSeriesMarkers = (lc as any).createSeriesMarkers;

        if (isDisposed || !containerRef.current) return;
        containerRef.current.innerHTML = "";

        const width =
          containerRef.current.clientWidth ||
          containerRef.current.parentElement?.clientWidth ||
          600;
        const height = containerRef.current.clientHeight || 380;

        chart = createChart(containerRef.current, {
          width: width,
          height: height,
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

        // Series creation compatible with both v5 (addSeries(CandlestickSeries)) and v4 (addCandlestickSeries)
        let candleSeries: any;
        const seriesOptions = {
          upColor: "#10b981",
          downColor: "#ef4444",
          borderVisible: false,
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
        };

        if (typeof chart.addSeries === "function" && CandlestickSeries) {
          candleSeries = chart.addSeries(CandlestickSeries, seriesOptions);
        } else if (typeof chart.addCandlestickSeries === "function") {
          candleSeries = chart.addCandlestickSeries(seriesOptions);
        } else if (typeof chart.addSeries === "function") {
          candleSeries = chart.addSeries("Candlestick", seriesOptions);
        }

        candleSeries.setData(sanitizedBars);

        // Trade markers
        if (trades.length > 0 && candleSeries) {
          const markers: any[] = [];
          trades.forEach((t) => {
            const entryTime = Math.floor(new Date(t.entry_ts).getTime() / 1000);
            const exitTime = Math.floor(new Date(t.exit_ts).getTime() / 1000);

            if (!isNaN(entryTime) && entryTime > 0) {
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
            }

            if (!isNaN(exitTime) && exitTime > 0) {
              markers.push({
                time: exitTime,
                position: t.side === "long" ? "aboveBar" : "belowBar",
                color: t.pnl >= 0 ? "#10b981" : "#ef4444",
                shape: "circle",
                text: `${t.exit_reason} (${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(0)})`,
              });
            }
          });

          // Sort markers chronologically
          markers.sort((a, b) => a.time - b.time);

          if (markers.length > 0) {
            if (typeof createSeriesMarkers === "function") {
              createSeriesMarkers(candleSeries, markers);
            } else if (typeof candleSeries.setMarkers === "function") {
              candleSeries.setMarkers(markers);
            }
          }
        }

        chart.timeScale().fitContent();

        // Responsive resize observer ensuring non-zero canvas dimensions
        if (typeof ResizeObserver !== "undefined" && containerRef.current) {
          resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
              if (entry.target === containerRef.current && chart) {
                const { width: w, height: h } = entry.contentRect;
                if (w > 0) {
                  chart.applyOptions({
                    width: w,
                    height: h > 0 ? h : 380,
                  });
                }
              }
            }
          });
          resizeObserver.observe(containerRef.current);
        }

        const handleWindowResize = () => {
          if (containerRef.current && chart) {
            const w = containerRef.current.clientWidth;
            if (w > 0) {
              chart.applyOptions({ width: w });
            }
          }
        };

        window.addEventListener("resize", handleWindowResize);

        return () => {
          window.removeEventListener("resize", handleWindowResize);
          if (resizeObserver) {
            resizeObserver.disconnect();
          }
        };
      } catch (err) {
        console.warn("Lightweight charts failed to render:", err);
      }
    };

    initChart();

    return () => {
      isDisposed = true;
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (chart) {
        chart.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [sanitizedBars, trades]);

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg overflow-hidden flex flex-col shadow-sm">
      <div className="flex items-center justify-between px-4 py-2 border-b border-surfaceBorder bg-[#0c1018]">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono font-bold text-white tracking-wider">{symbol}</span>
          <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
            {timeframe}
          </span>
          <span className="text-xs text-gray-400 font-mono">
            ({renderedBarCount} closed bars)
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

      <div className="relative w-full h-[380px] min-h-[380px] bg-[#0d111a]">
        <div ref={containerRef} className="w-full h-[380px] min-h-[380px]" />
        {sanitizedBars.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6 bg-[#0d111a]/95 z-10">
            <div className="w-7 h-7 rounded-full border-2 border-accent border-t-transparent animate-spin mb-3"></div>
            <div className="text-xs font-mono text-gray-200">
              Awaiting market data for {symbol} ({timeframe})...
            </div>
            <div className="text-[11px] font-mono text-gray-500 mt-1">
              Querying yfinance cache & historical ohlcv_bars database
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
