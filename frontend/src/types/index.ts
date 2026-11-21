export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  workspaces: Workspace[];
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  role: string;
  created_at: string;
}

export interface StrategyVersion {
  id: string;
  strategy_id: string;
  version_number: number;
  parameters: Record<string, any>;
  code_hash: string;
  is_locked: boolean;
  created_at: string;
}

export interface Strategy {
  id: string;
  workspace_id: string;
  user_id: string;
  name: string;
  description?: string;
  strategy_type: "rsi" | "divergence" | string;
  is_live: boolean;
  created_at: string;
  latest_version?: StrategyVersion;
}

export interface BacktestRun {
  id: string;
  strategy_version_id: string;
  workspace_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  config_hash: string;
  symbol: string;
  timeframe: string;
  start_ts?: string;
  end_ts?: string;
  initial_capital: number;
  final_equity?: number;
  slippage_bps: number;
  commission_per_trade: number;
  spread_pips: number;
  total_return?: number;
  cagr?: number;
  sharpe_ratio?: number;
  sortino_ratio?: number;
  calmar_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  profit_factor?: number;
  total_trades?: number;
  winning_trades?: number;
  losing_trades?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface TradeItem {
  trade_number: number;
  symbol: string;
  side: "long" | "short";
  entry_ts: string;
  exit_ts: string;
  entry_price: number;
  exit_price: number;
  size: number;
  pnl: number;
  gross_pnl: number;
  return_pct: number;
  commission: number;
  slippage: number;
  exit_reason: string;
  bars_held: number;
}

export interface EquityPoint {
  ts: string;
  equity: number;
  cash: number;
  drawdown: number;
  drawdown_pct: number;
  returns: number;
}

export interface Tearsheet {
  run: BacktestRun;
  strategy_name: string;
  strategy_type: string;
  parameters: Record<string, any>;
  metrics: Record<string, any>;
  recent_trades: TradeItem[];
  equity_curve: EquityPoint[];
}

export interface StrategySpecOutput {
  hypothesis_summary: string;
  strategy_type: "rsi" | "divergence";
  symbol: string;
  timeframe: string;
  parameters: Record<string, any>;
  parameter_breakdown: Array<{
    name: string;
    value: any;
    type: string;
    description: string;
    bounds_applied?: string;
  }>;
  validation_findings: Array<{
    severity: "INFO" | "WARNING" | "ERROR";
    message: string;
    recommendation: string;
  }>;
  human_confirmation_required: boolean;
  disclaimer: string;
}

export interface BacktestCritiqueOutput {
  run_id: string;
  executive_summary: string;
  exact_metrics_cited: Record<string, any>;
  overfitting_analysis: {
    risk_level: "LOW" | "MODERATE" | "HIGH" | "SEVERE";
    sample_size_flag: boolean;
    trade_count_observed: number;
    parameter_sensitivity_warning?: string;
    rationale: string;
  };
  drawdown_critique: {
    max_drawdown_pct: number;
    max_drawdown_dollars: number;
    max_drawdown_duration_bars: number;
    recovery_assessment: string;
  };
  regime_breakdown: Array<{
    regime: string;
    suitability: "FAVORABLE" | "NEUTRAL" | "UNFAVORABLE";
    observed_metric_note: string;
  }>;
  key_strengths: string[];
  key_vulnerabilities: string[];
  actionable_recommendations: string[];
  disclaimer: string;
}

export interface OHLCVBar {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
