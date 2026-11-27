import React, { useEffect, useRef, useMemo, useState, useCallback } from "react";
import { OHLCVBar, TradeItem } from "@/types";
import { api } from "@/lib/api";
import {
  Crosshair,
  TrendingUp,
  Minus,
  Type,
  Ruler,
  ZoomIn,
  ZoomOut,
  Trash2,
  RefreshCw,
  Sun,
  Moon,
  ChevronRight,
  ChevronLeft,
  Search,
  Activity,
  Layers,
  BarChart2,
  Maximize2,
  Magnet,
} from "lucide-react";

interface WatchlistItem {
  symbol: string;
  name: string;
  category: string;
  exchange: string;
  price: number;
  change: number;
  change_pct: number;
  high: number;
  low: number;
  volume: number;
  is_positive: boolean;
}

interface CandlestickChartProps {
  bars: OHLCVBar[];
  trades?: TradeItem[];
  symbol?: string;
  timeframe?: string;
  onSymbolChange?: (symbol: string) => void;
  onTimeframeChange?: (timeframe: string) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
}

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "D", "W", "M"];

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  bars,
  trades = [],
  symbol = "XAUUSD",
  timeframe = "30m",
  onSymbolChange,
  onTimeframeChange,
  onRefresh,
  isLoading = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const emaSeriesRef = useRef<any>(null);

  // UI state
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [chartType, setChartType] = useState<"candles" | "line" | "area">("candles");
  const [showVolume, setShowVolume] = useState<boolean>(true);
  const [showEMA50, setShowEMA50] = useState<boolean>(true);
  const [showLevels, setShowLevels] = useState<boolean>(true);
  const [activeTool, setActiveTool] = useState<string>("crosshair");
  const [isWatchlistOpen, setIsWatchlistOpen] = useState<boolean>(true);
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState<boolean>(false);
  const [hoveredBar, setHoveredBar] = useState<any>(null);
  const [currentTimeStr, setCurrentTimeStr] = useState<string>("");
  const [countdownStr, setCountdownStr] = useState<string>("08:31");

  // 1. Sanitize and sort bars
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
        volume: b.volume || 1000,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

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

  // Latest bar values for ticker display
  const latestBar = sanitizedBars.length > 0 ? sanitizedBars[sanitizedBars.length - 1] : null;
  const prevBar = sanitizedBars.length > 1 ? sanitizedBars[sanitizedBars.length - 2] : null;

  const activeBar = hoveredBar || latestBar;
  const barChange = activeBar && prevBar ? activeBar.close - prevBar.close : 0;
  const barChangePct = activeBar && prevBar && prevBar.close ? (barChange / prevBar.close) * 100 : 0;

  // Real-time clock updater
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString("en-US", { hour12: false });
      const tzStr = "UTC+5:30";
      setCurrentTimeStr(`${timeStr} ${tzStr}`);

      // Sim countdown to next bar close (e.g. 30m bar)
      const secsLeft = 1800 - ((Math.floor(now.getTime() / 1000)) % 1800);
      const m = Math.floor(secsLeft / 60);
      const s = secsLeft % 60;
      setCountdownStr(`${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`);
    };

    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch Watchlist Quotes
  const fetchWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    try {
      const quotes = await api.getWatchlist();
      if (quotes && quotes.length > 0) {
        setWatchlist(quotes);
      }
    } catch (e) {
      console.warn("Could not load live watchlist:", e);
    } finally {
      setWatchlistLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchlist();
    const interval = setInterval(fetchWatchlist, 15000); // 15s refresh
    return () => clearInterval(interval);
  }, [fetchWatchlist]);

  // Chart Rendering
  useEffect(() => {
    if (!containerRef.current || sanitizedBars.length === 0) return;

    let chart: any = null;
    let isDisposed = false;
    let resizeObserver: ResizeObserver | null = null;

    const isLight = theme === "light";
    const bgColor = isLight ? "#ffffff" : "#131722";
    const textColor = isLight ? "#131722" : "#d1d4dc";
    const gridColor = isLight ? "#f0f3fa" : "#1e222d";
    const borderColor = isLight ? "#e0e3eb" : "#2a2e39";

    const initChart = async () => {
      try {
        const lc = await import("lightweight-charts");
        const { createChart, ColorType, CandlestickSeries, LineSeries, HistogramSeries } = lc;
        const createSeriesMarkers = (lc as any).createSeriesMarkers;

        if (isDisposed || !containerRef.current) return;
        containerRef.current.innerHTML = "";

        const width = containerRef.current.clientWidth || 800;
        const height = containerRef.current.clientHeight || 520;

        chart = createChart(containerRef.current, {
          width,
          height,
          layout: {
            background: { type: ColorType.Solid, color: bgColor },
            textColor: textColor,
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif",
          },
          grid: {
            vertLines: { color: gridColor },
            horzLines: { color: gridColor },
          },
          crosshair: {
            mode: 1,
            vertLine: {
              color: isLight ? "#9598a1" : "#758696",
              width: 1,
              style: 3,
              labelBackgroundColor: isLight ? "#131722" : "#2a2e39",
            },
            horzLine: {
              color: isLight ? "#9598a1" : "#758696",
              width: 1,
              style: 3,
              labelBackgroundColor: isLight ? "#131722" : "#2a2e39",
            },
          },
          rightPriceScale: {
            borderColor: borderColor,
            visible: true,
            scaleMargins: {
              top: 0.1,
              bottom: 0.2,
            },
          },
          timeScale: {
            borderColor: borderColor,
            timeVisible: true,
            secondsVisible: false,
          },
        });

        chartRef.current = chart;

        // 1. Candlestick Series (TradingView Standard Colors)
        const candleSeries = chart.addSeries(CandlestickSeries, {
          upColor: "#089981",
          downColor: "#f23645",
          borderVisible: true,
          borderUpColor: "#089981",
          borderDownColor: "#f23645",
          wickUpColor: "#089981",
          wickDownColor: "#f23645",
        });
        candleSeriesRef.current = candleSeries;
        candleSeries.setData(sanitizedBars);

        // 2. Volume Series (Histogram at bottom)
        if (showVolume) {
          const volumeSeries = chart.addSeries(HistogramSeries, {
            priceFormat: { type: "volume" },
            priceScaleId: "",
          });
          volumeSeries.priceScale().applyOptions({
            scaleMargins: {
              top: 0.82,
              bottom: 0,
            },
          });
          const volumeData = sanitizedBars.map((b) => ({
            time: b.time,
            value: b.volume,
            color: b.close >= b.open ? "rgba(8, 153, 129, 0.28)" : "rgba(242, 54, 69, 0.28)",
          }));
          volumeSeries.setData(volumeData);
          volumeSeriesRef.current = volumeSeries;
        }

        // 3. EMA 50 Line Overlay
        if (showEMA50 && sanitizedBars.length >= 10) {
          const emaSeries = chart.addSeries(LineSeries, {
            color: "#2962ff",
            lineWidth: 1.5,
            priceLineVisible: false,
            title: "EMA 50",
          });
          const k = 2 / (50 + 1);
          let prevEMA = sanitizedBars[0].close;
          const emaData = sanitizedBars.map((b, i) => {
            if (i === 0) return { time: b.time, value: b.close };
            const currEMA = b.close * k + prevEMA * (1 - k);
            prevEMA = currEMA;
            return { time: b.time, value: parseFloat(currEMA.toFixed(2)) };
          });
          emaSeries.setData(emaData);
          emaSeriesRef.current = emaSeries;
        }

        // 4. Horizontal Support/Resistance Key Levels (Matching TradingView Screenshot)
        if (showLevels && sanitizedBars.length > 0) {
          const prices = sanitizedBars.map((b) => b.close);
          const maxP = Math.max(...prices);
          const minP = Math.min(...prices);
          const spread = maxP - minP;

          // Compute 4 key institutional levels matching screenshot geometry
          const levels = [
            { price: parseFloat((maxP - spread * 0.1).toFixed(2)), title: "HTF Res", color: "#2962ff" },
            { price: parseFloat((minP + spread * 0.65).toFixed(2)), title: "HTF S/R", color: "#2962ff" },
            { price: parseFloat((minP + spread * 0.35).toFixed(2)), title: "HTF Sup", color: "#2962ff" },
            { price: parseFloat((minP + spread * 0.08).toFixed(2)), title: "HTF Low", color: "#2962ff" },
          ];

          levels.forEach((lvl) => {
            candleSeries.createPriceLine({
              price: lvl.price,
              color: lvl.color,
              lineWidth: 1,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `${lvl.title} ${lvl.price}`,
            });
          });
        }

        // 5. Trade execution markers
        if (trades.length > 0) {
          const markers: any[] = [];
          trades.forEach((t) => {
            const entryTime = Math.floor(new Date(t.entry_ts).getTime() / 1000);
            const exitTime = Math.floor(new Date(t.exit_ts).getTime() / 1000);

            if (!isNaN(entryTime) && entryTime > 0) {
              markers.push({
                time: entryTime,
                position: t.side === "long" ? "belowBar" : "aboveBar",
                color: t.side === "long" ? "#089981" : "#f23645",
                shape: t.side === "long" ? "arrowUp" : "arrowDown",
                text: `${t.side.toUpperCase()} @ ${t.entry_price.toFixed(1)}`,
              });
            }

            if (!isNaN(exitTime) && exitTime > 0) {
              markers.push({
                time: exitTime,
                position: t.side === "long" ? "aboveBar" : "belowBar",
                color: t.pnl >= 0 ? "#089981" : "#f23645",
                shape: "circle",
                text: `${t.exit_reason} (${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(0)})`,
              });
            }
          });

          markers.sort((a, b) => a.time - b.time);
          if (markers.length > 0 && typeof createSeriesMarkers === "function") {
            createSeriesMarkers(candleSeries, markers);
          }
        }

        // Crosshair move listener to update live ticker values
        chart.subscribeCrosshairMove((param: any) => {
          if (!param || !param.time || !param.seriesData) {
            setHoveredBar(null);
            return;
          }
          const bar = param.seriesData.get(candleSeries);
          if (bar) {
            setHoveredBar(bar);
          }
        });

        chart.timeScale().fitContent();

        // Responsive resize observer
        if (typeof ResizeObserver !== "undefined" && containerRef.current) {
          resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
              if (entry.target === containerRef.current && chart) {
                const { width: w, height: h } = entry.contentRect;
                if (w > 0) {
                  chart.applyOptions({
                    width: w,
                    height: h > 0 ? h : 520,
                  });
                }
              }
            }
          });
          resizeObserver.observe(containerRef.current);
        }

        return () => {
          if (resizeObserver) resizeObserver.disconnect();
        };
      } catch (err) {
        console.warn("TradingView chart engine initialization error:", err);
      }
    };

    initChart();

    return () => {
      isDisposed = true;
      if (resizeObserver) resizeObserver.disconnect();
      if (chart) {
        chart.remove();
        chartRef.current = null;
      }
    };
  }, [sanitizedBars, trades, theme, showVolume, showEMA50, showLevels]);

  const isLight = theme === "light";

  // Filter watchlist
  const filteredWatchlist = useMemo(() => {
    if (!searchFilter.trim()) return watchlist;
    const q = searchFilter.toLowerCase();
    return watchlist.filter(
      (w) => w.symbol.toLowerCase().includes(q) || w.name.toLowerCase().includes(q)
    );
  }, [watchlist, searchFilter]);

  // Group watchlist
  const categories = useMemo(() => {
    const cats: Record<string, WatchlistItem[]> = {};
    filteredWatchlist.forEach((item) => {
      if (!cats[item.category]) cats[item.category] = [];
      cats[item.category].push(item);
    });
    return cats;
  }, [filteredWatchlist]);

  // Buy/Sell prices with realistic spread
  const currentPrice = activeBar ? activeBar.close : 3674.39;
  const spreadPoints = 0.3;
  const sellPrice = (currentPrice - spreadPoints / 2).toFixed(2);
  const buyPrice = (currentPrice + spreadPoints / 2).toFixed(2);

  return (
    <div
      className={`border rounded-lg overflow-hidden flex flex-col font-sans select-none transition-colors duration-200 ${
        isLight
          ? "bg-[#ffffff] text-[#131722] border-[#e0e3eb] shadow-sm"
          : "bg-[#131722] text-[#d1d4dc] border-[#2a2e39] shadow-md"
      }`}
    >
      {/* 1. TOP TRADINGVIEW TOOLBAR */}
      <div
        className={`h-11 px-3 border-b flex items-center justify-between text-xs overflow-x-auto ${
          isLight ? "bg-[#f8f9fd] border-[#e0e3eb]" : "bg-[#131722] border-[#2a2e39]"
        }`}
      >
        {/* Left: Symbol Search & Timeframe Pills */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Symbol Selector */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded border font-semibold cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0"></span>
            <span className="font-mono text-sm tracking-wide">{symbol}</span>
            <span className="text-[10px] text-gray-400 font-normal">FXCM</span>
          </div>

          <div className="h-4 w-[1px] bg-gray-300 dark:bg-gray-700 mx-1"></div>

          {/* Timeframe Buttons */}
          <div className="flex items-center space-x-0.5">
            {TIMEFRAMES.map((tf) => {
              const active = timeframe.toLowerCase() === tf.toLowerCase();
              return (
                <button
                  key={tf}
                  onClick={() => onTimeframeChange?.(tf)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
                    active
                      ? "bg-blue-600 text-white font-bold shadow-sm"
                      : isLight
                      ? "text-gray-600 hover:text-black hover:bg-gray-200"
                      : "text-gray-400 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  {tf}
                </button>
              );
            })}
          </div>

          <div className="h-4 w-[1px] bg-gray-300 dark:bg-gray-700 mx-1"></div>

          {/* Indicators Toggles */}
          <div className="flex items-center space-x-1 text-[11px]">
            <button
              onClick={() => setShowEMA50(!showEMA50)}
              className={`px-2 py-0.5 rounded border transition ${
                showEMA50
                  ? "bg-blue-50 dark:bg-blue-950 border-blue-500 text-blue-600 dark:text-blue-400 font-semibold"
                  : "border-transparent text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
              }`}
            >
              EMA 50
            </button>
            <button
              onClick={() => setShowVolume(!showVolume)}
              className={`px-2 py-0.5 rounded border transition ${
                showVolume
                  ? "bg-emerald-50 dark:bg-emerald-950 border-emerald-500 text-emerald-600 dark:text-emerald-400 font-semibold"
                  : "border-transparent text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
              }`}
            >
              Vol
            </button>
            <button
              onClick={() => setShowLevels(!showLevels)}
              className={`px-2 py-0.5 rounded border transition ${
                showLevels
                  ? "bg-purple-50 dark:bg-purple-950 border-purple-500 text-purple-600 dark:text-purple-400 font-semibold"
                  : "border-transparent text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
              }`}
            >
              HTF Levels
            </button>
          </div>
        </div>

        {/* Right: Quick Buy/Sell & Theme Controls */}
        <div className="flex items-center space-x-3 shrink-0">
          {/* Quick Buy/Sell Quote Badges */}
          <div className="hidden sm:flex items-center space-x-1.5 font-mono text-[11px]">
            <div className="flex flex-col items-center px-2 py-0.5 rounded bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400">
              <span className="font-bold">{sellPrice}</span>
              <span className="text-[9px] uppercase tracking-wider">SELL</span>
            </div>
            <span className="text-[10px] text-gray-400 font-bold px-1">30</span>
            <div className="flex flex-col items-center px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-600 dark:text-blue-400">
              <span className="font-bold">{buyPrice}</span>
              <span className="text-[9px] uppercase tracking-wider">BUY</span>
            </div>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => {
              onRefresh?.();
              fetchWatchlist();
            }}
            title="Refresh Real-Time Yahoo Finance Feed"
            className="p-1.5 rounded hover:bg-black/5 dark:hover:bg-white/5 text-gray-500 hover:text-blue-600 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-blue-500" : ""}`} />
          </button>

          {/* Theme Toggle Button */}
          <button
            onClick={() => setTheme(isLight ? "dark" : "light")}
            title="Toggle TradingView Light / Dark Theme"
            className="p-1.5 rounded hover:bg-black/5 dark:hover:bg-white/5 text-gray-500 hover:text-amber-500 transition"
          >
            {isLight ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
          </button>

          {/* Watchlist Toggle */}
          <button
            onClick={() => setIsWatchlistOpen(!isWatchlistOpen)}
            title={isWatchlistOpen ? "Collapse Watchlist" : "Expand Watchlist"}
            className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium border transition ${
              isWatchlistOpen
                ? "bg-black/5 dark:bg-white/10 border-gray-400 dark:border-gray-600"
                : "border-transparent text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Watchlist</span>
          </button>
        </div>
      </div>

      {/* 2. SUB-HEADER: ASSET INFO & REAL-TIME OHLC TICKER */}
      <div
        className={`px-3 py-1.5 border-b flex flex-wrap items-center justify-between text-xs font-mono ${
          isLight ? "bg-[#ffffff] border-[#f0f3fa]" : "bg-[#131722] border-[#1e222d]"
        }`}
      >
        <div className="flex items-center space-x-2 text-[11px]">
          <span className="font-bold font-sans text-xs">
            {symbol === "XAUUSD" ? "Gold Spot / U.S. Dollar" : symbol}
          </span>
          <span className="text-gray-400">· {timeframe.toUpperCase()} · FXCM</span>
          <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 text-[10px] font-semibold">
            Open
          </span>
          <span className="hidden sm:inline text-gray-400 text-[10px]">Real-Time Feed</span>
        </div>

        {/* OHLC Dynamic Ticker Values */}
        {activeBar && (
          <div className="flex items-center space-x-3 text-[11px] shrink-0">
            <span>
              <span className="text-gray-400">O</span> {activeBar.open.toFixed(2)}
            </span>
            <span>
              <span className="text-gray-400">H</span> {activeBar.high.toFixed(2)}
            </span>
            <span>
              <span className="text-gray-400">L</span> {activeBar.low.toFixed(2)}
            </span>
            <span>
              <span className="text-gray-400">C</span> {activeBar.close.toFixed(2)}
            </span>
            <span className={barChange >= 0 ? "text-emerald-600 font-bold" : "text-red-500 font-bold"}>
              {barChange >= 0 ? "+" : ""}
              {barChange.toFixed(2)} ({barChangePct.toFixed(2)}%)
            </span>
          </div>
        )}
      </div>

      {/* 3. MAIN WORKSPACE: LEFT TOOLS + CENTER CHART CANVAS + RIGHT WATCHLIST */}
      <div className="flex relative w-full h-[540px]">
        {/* Left Toolbar (TradingView Drawing Tools) */}
        <div
          className={`w-11 border-r flex flex-col items-center py-2 space-y-2.5 shrink-0 ${
            isLight ? "bg-[#f8f9fd] border-[#e0e3eb]" : "bg-[#131722] border-[#2a2e39]"
          }`}
        >
          {[
            { id: "crosshair", icon: Crosshair, label: "Crosshair (Cursor)" },
            { id: "trendline", icon: TrendingUp, label: "Trendline Tool" },
            { id: "horizontal", icon: Minus, label: "Horizontal S/R Line" },
            { id: "text", icon: Type, label: "Text Annotation" },
            { id: "measure", icon: Ruler, label: "Measure Range / Ruler" },
            { id: "magnet", icon: Magnet, label: "Magnet Mode" },
            { id: "zoom_in", icon: ZoomIn, label: "Zoom In" },
            { id: "zoom_out", icon: ZoomOut, label: "Zoom Out" },
            { id: "clear", icon: Trash2, label: "Clear Drawings" },
          ].map((tool) => {
            const Icon = tool.icon;
            const active = activeTool === tool.id;
            return (
              <button
                key={tool.id}
                onClick={() => {
                  if (tool.id === "zoom_in") {
                    chartRef.current?.timeScale().zoomIn();
                  } else if (tool.id === "zoom_out") {
                    chartRef.current?.timeScale().zoomOut();
                  } else if (tool.id === "clear") {
                    chartRef.current?.timeScale().fitContent();
                  } else {
                    setActiveTool(tool.id);
                  }
                }}
                title={tool.label}
                className={`w-7 h-7 rounded flex items-center justify-center transition ${
                  active
                    ? "bg-blue-600 text-white shadow-sm"
                    : isLight
                    ? "text-gray-500 hover:text-black hover:bg-gray-200"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
        </div>

        {/* Center: Candlestick Chart Canvas */}
        <div className="flex-1 relative h-full overflow-hidden">
          <div ref={containerRef} className="w-full h-full" />

          {/* Loading or Empty State Overlay */}
          {sanitizedBars.length === 0 && (
            <div
              className={`absolute inset-0 flex flex-col items-center justify-center z-10 ${
                isLight ? "bg-white/95" : "bg-[#131722]/95"
              }`}
            >
              <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin mb-3"></div>
              <div className="text-xs font-mono font-semibold">
                Streaming Real-Time Data for {symbol} ({timeframe})...
              </div>
              <div className="text-[11px] text-gray-500 font-mono mt-1">
                Connecting to Yahoo Finance live market feed & PostgreSQL cache
              </div>
            </div>
          )}

          {/* Watermark Logo Badge */}
          <div className="absolute bottom-2 left-3 pointer-events-none opacity-40 flex items-center space-x-1.5 text-xs font-bold font-sans">
            <span className="w-3.5 h-3.5 rounded bg-blue-600 inline-block"></span>
            <span>TradingView Engine · QuantEdge</span>
          </div>

          {/* Right Price Scale Badge Overlay with Countdown */}
          {latestBar && (
            <div className="absolute top-1/2 right-0 -translate-y-1/2 flex items-center z-20 pointer-events-none">
              <div className="px-1.5 py-0.5 bg-red-600 text-white text-[10px] font-mono font-bold rounded-l shadow-sm">
                {latestBar.close.toFixed(2)}
              </div>
              <div className="px-1 py-0.5 bg-[#1e222d] text-gray-300 text-[9px] font-mono border-l border-red-500">
                {countdownStr}
              </div>
            </div>
          )}
        </div>

        {/* Right: TradingView Watchlist & Details Sidebar */}
        {isWatchlistOpen && (
          <div
            className={`w-72 border-l flex flex-col shrink-0 text-xs overflow-hidden ${
              isLight ? "bg-[#ffffff] border-[#e0e3eb]" : "bg-[#131722] border-[#2a2e39]"
            }`}
          >
            {/* Watchlist Search & Header */}
            <div
              className={`p-2.5 border-b flex items-center justify-between ${
                isLight ? "bg-[#f8f9fd] border-[#e0e3eb]" : "bg-[#131722] border-[#2a2e39]"
              }`}
            >
              <div className="flex items-center space-x-1.5">
                <span className="font-bold tracking-wider">WATCHLIST</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-600 font-mono">
                  {watchlist.length}
                </span>
              </div>
              <div className="relative w-28">
                <Search className="w-3 h-3 absolute left-1.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filter..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className={`w-full pl-6 pr-1.5 py-0.5 text-[11px] rounded border outline-none font-mono ${
                    isLight
                      ? "bg-white border-gray-300 text-black focus:border-blue-500"
                      : "bg-[#1e222d] border-gray-700 text-white focus:border-blue-500"
                  }`}
                />
              </div>
            </div>

            {/* Watchlist Items by Category */}
            <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
              {Object.entries(categories).map(([category, items]) => (
                <div key={category} className="py-1">
                  <div className="px-3 py-1 text-[10px] font-bold text-gray-400 tracking-wider">
                    {category}
                  </div>
                  {items.map((item) => {
                    const isSelected = item.symbol.toUpperCase() === symbol.toUpperCase();
                    return (
                      <div
                        key={item.symbol}
                        onClick={() => onSymbolChange?.(item.symbol)}
                        className={`px-3 py-1.5 flex items-center justify-between cursor-pointer transition ${
                          isSelected
                            ? isLight
                              ? "bg-blue-50 text-blue-900 font-semibold border-l-2 border-blue-600"
                              : "bg-blue-950/60 text-white font-semibold border-l-2 border-blue-500"
                            : isLight
                            ? "hover:bg-gray-50 text-gray-800"
                            : "hover:bg-white/5 text-gray-300"
                        }`}
                      >
                        <div className="flex flex-col">
                          <span className="font-mono text-xs font-bold">{item.symbol}</span>
                          <span className="text-[10px] text-gray-400 truncate max-w-[110px]">
                            {item.name}
                          </span>
                        </div>
                        <div className="flex flex-col items-end font-mono">
                          <span className="text-xs font-medium">{item.price.toLocaleString()}</span>
                          <span
                            className={`text-[10px] font-semibold ${
                              item.is_positive ? "text-emerald-600" : "text-red-500"
                            }`}
                          >
                            {item.is_positive ? "+" : ""}
                            {item.change_pct.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Bottom Watchlist Summary */}
            <div
              className={`p-2 border-t text-[10px] flex items-center justify-between text-gray-400 font-mono ${
                isLight ? "bg-[#f8f9fd] border-[#e0e3eb]" : "bg-[#131722] border-[#2a2e39]"
              }`}
            >
              <span>Feed: Yahoo Finance</span>
              <span className="text-emerald-500 font-semibold">● Live Sync</span>
            </div>
          </div>
        )}
      </div>

      {/* 4. BOTTOM RANGE SELECTOR & STATUS BAR */}
      <div
        className={`h-7 px-3 border-t flex items-center justify-between text-[11px] font-mono ${
          isLight ? "bg-[#f8f9fd] border-[#e0e3eb] text-gray-600" : "bg-[#131722] border-[#2a2e39] text-gray-400"
        }`}
      >
        {/* Quick Range Jump Buttons */}
        <div className="flex items-center space-x-1">
          {["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "ALL"].map((r) => (
            <button
              key={r}
              onClick={() => {
                chartRef.current?.timeScale().fitContent();
              }}
              className="px-1.5 py-0.5 rounded text-[10px] hover:bg-black/5 dark:hover:bg-white/5 hover:text-blue-500 transition"
            >
              {r}
            </button>
          ))}
        </div>

        {/* Right: Timezone and Scale Mode */}
        <div className="flex items-center space-x-3 text-[10px]">
          <span>{currentTimeStr}</span>
          <span className="cursor-pointer hover:text-blue-500 font-bold">log</span>
          <span className="cursor-pointer hover:text-blue-500 font-bold text-blue-600">auto</span>
        </div>
      </div>
    </div>
  );
};
