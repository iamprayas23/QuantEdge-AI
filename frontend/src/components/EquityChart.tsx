import React from "react";
import { EquityPoint } from "@/types";

interface EquityChartProps {
  equityCurve: EquityPoint[];
  initialCapital?: number;
}

export const EquityChart: React.FC<EquityChartProps> = ({
  equityCurve,
  initialCapital = 10000,
}) => {
  if (!equityCurve || equityCurve.length === 0) {
    return (
      <div className="bg-surface border border-surfaceBorder rounded-lg p-6 text-center text-gray-500 font-mono text-xs">
        No equity curve data available. Launch a backtest to generate tearsheet curves.
      </div>
    );
  }

  // Calculate coordinates for SVG
  const width = 800;
  const height = 240;
  const padding = { top: 20, right: 20, bottom: 30, left: 60 };

  const equities = equityCurve.map((p) => p.equity);
  const minEquity = Math.min(...equities, initialCapital * 0.95);
  const maxEquity = Math.max(...equities, initialCapital * 1.05);

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const points = equityCurve.map((pt, i) => {
    const x = padding.left + (i / (equityCurve.length - 1)) * innerWidth;
    const y =
      padding.top +
      innerHeight -
      ((pt.equity - minEquity) / (maxEquity - minEquity || 1)) * innerHeight;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(" L ")}`;
  const baselineY =
    padding.top +
    innerHeight -
    ((initialCapital - minEquity) / (maxEquity - minEquity || 1)) * innerHeight;

  // Underwater drawdown curve points (0% to -maxDD)
  const ddPoints = equityCurve.map((pt, i) => {
    const x = padding.left + (i / (equityCurve.length - 1)) * innerWidth;
    // Cap dd scale at 30%
    const ddFraction = Math.min(pt.drawdown_pct / 30.0, 1.0);
    const y = padding.top + innerHeight - (1.0 - ddFraction) * (innerHeight * 0.35);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <div className="bg-surface border border-surfaceBorder rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-mono font-bold text-white tracking-wider">
          EQUITY TRAJECTORY & UNDERWATER CURVE
        </div>
        <div className="text-xs font-mono text-gray-400">
          Base Capital: ${initialCapital.toLocaleString()}
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[220px]">
          {/* Background Grid */}
          <line
            x1={padding.left}
            y1={baselineY}
            x2={width - padding.right}
            y2={baselineY}
            stroke="#1e293b"
            strokeDasharray="4 4"
            strokeWidth="1"
          />

          {/* Equity Line */}
          <path
            d={pathD}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Labels */}
          <text
            x={padding.left - 8}
            y={padding.top + 10}
            fill="#94a3b8"
            fontSize="10"
            fontFamily="monospace"
            textAnchor="end"
          >
            ${maxEquity.toFixed(0)}
          </text>
          <text
            x={padding.left - 8}
            y={baselineY + 3}
            fill="#64748b"
            fontSize="9"
            fontFamily="monospace"
            textAnchor="end"
          >
            $10k
          </text>
          <text
            x={padding.left - 8}
            y={height - padding.bottom}
            fill="#94a3b8"
            fontSize="10"
            fontFamily="monospace"
            textAnchor="end"
          >
            ${minEquity.toFixed(0)}
          </text>

          {/* Date boundaries */}
          <text
            x={padding.left}
            y={height - 8}
            fill="#64748b"
            fontSize="9"
            fontFamily="monospace"
          >
            {equityCurve[0].ts.slice(0, 10)}
          </text>
          <text
            x={width - padding.right}
            y={height - 8}
            fill="#64748b"
            fontSize="9"
            fontFamily="monospace"
            textAnchor="end"
          >
            {equityCurve[equityCurve.length - 1].ts.slice(0, 10)}
          </text>
        </svg>
      </div>
    </div>
  );
};
