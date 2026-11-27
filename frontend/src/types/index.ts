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

export interface AnalystSignal {
  agent_name: string;
  signal: "BULLISH" | "BEARISH" | "NEUTRAL";
  confidence: number;
  rationale: string;
  metrics_grounding: Record<string, any>;
  suggested_adjustments?: Record<string, any>;
}

export interface RiskAssessment {
  max_risk_per_trade_pct: number;
  max_drawdown_limit_pct: number;
  allowed_action: "PERMIT" | "RESTRICT" | "HALT";
  volatility_assessment: string;
  risk_warnings: string[];
  rationale: string;
}

export interface PortfolioProposal {
  target_action: "BUY" | "SELL" | "HOLD";
  recommended_parameters: Record<string, any>;
  target_allocation_pct: number;
  risk_per_trade_pct: number;
  stop_loss_atr_mult: number;
  take_profit_atr_mult: number;
  execution_urgency: "PATIENT" | "NORMAL" | "IMMEDIATE";
  reasoning: string;
  human_confirmation_required: boolean;
}

export interface CommitteeReviewOutput {
  id: string;
  symbol: string;
  timeframe: string;
  as_of_ts: string;
  strategy_version_id?: string;
  backtest_run_id?: string;
  analyst_signals: Record<string, AnalystSignal>;
  risk_assessment: RiskAssessment;
  portfolio_proposal: PortfolioProposal;
  executive_summary: string;
  human_confirmation_required: boolean;
  disclaimer: string;
}

export interface CommitteeReportSummary {
  id: string;
  symbol: string;
  timeframe: string;
  as_of_ts: string;
  portfolio_action: string;
  overall_confidence: number;
  executive_summary: string;
  created_at: string;
}

// =========================================================================
// 5 Finance & Trading Pillars Interfaces
// =========================================================================

// Pillar 1: Market Catalyst & Regime Context
export interface MarketCatalystEvent {
  id?: string;
  timestamp_utc: string;
  symbol: string;
  title: string;
  category: "macro" | "rates" | "liquidity" | "earnings" | "geopolitical" | string;
  impact: "HIGH" | "MEDIUM" | "LOW" | string;
  sentiment: "HAWKISH" | "DOVISH" | "BULLISH" | "BEARISH" | "NEUTRAL" | string;
  actual_value?: string;
  forecast_value?: string;
  previous_value?: string;
  source: string;
}

export interface CatalystBriefOutput {
  symbol: string;
  as_of_ts: string;
  current_regime: string;
  realized_vol_pct: number;
  active_or_upcoming_catalysts: Array<Record<string, any>>;
  recent_catalyst_shocks: Array<Record<string, any>>;
  catalyst_impact_metrics: Record<string, any>;
  executive_brief: string;
  risk_advisory: string;
  disclaimer: string;
}

// Pillar 2: Rule Discipline & Execution Guardrails
export interface RiskRuleProfile {
  id?: string;
  name: string;
  max_risk_per_trade_pct: number;
  daily_loss_limit_pct: number;
  daily_loss_limit_abs?: number;
  max_drawdown_pct: number;
  drawdown_mode: "static" | "trailing" | string;
  max_consecutive_losses: number;
  cooldown_bars: number;
  max_trades_per_day: number;
  max_gross_exposure_pct: number;
}

export interface RuleBreach {
  timestamp: string;
  rule_name: string;
  threshold: any;
  observed_value: any;
  severity: "WARNING" | "BREACH" | "CRITICAL";
  action_taken: string;
  message: string;
}

export interface GuardrailEvaluationResult {
  allowed: boolean;
  adjusted_size: number;
  breached_rules: RuleBreach[];
  rule_adherence_score: number;
  cooldown_remaining_bars: number;
  current_daily_pnl: number;
  current_drawdown_pct: number;
  consecutive_losses: number;
  trades_today: number;
  summary_verdict: string;
}

export interface GuardrailAuditReport {
  profile_name: string;
  total_trades_evaluated: number;
  compliant_trades: number;
  breach_count: number;
  rule_adherence_score: number;
  capital_lost_to_breaches: number;
  counterfactual_final_equity: number;
  actual_final_equity: number;
  disciplined_alpha_preserved: number;
  breach_breakdown: Record<string, number>;
  detailed_breaches: RuleBreach[];
  summary_recommendation: string;
}

// Pillar 3: Walk-Forward & Stress Testing
export interface WalkForwardWindowResult {
  window_index: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  selected_params: Record<string, any>;
  is_metrics: Record<string, any>;
  oos_metrics: Record<string, any>;
  wfe: number;
}

export interface WalkForwardAnalysisResult {
  strategy_type: string;
  symbol: string;
  timeframe: string;
  mode: string;
  num_windows: number;
  overall_wfe: number;
  parameter_stability_score: number;
  robustness_verdict: "ROBUST" | "BORDERLINE" | "OVERFIT" | string;
  windows: WalkForwardWindowResult[];
  stitched_oos_summary: Record<string, any>;
  summary_verdict: string;
}

export interface StressTestReport {
  scenario_name: string;
  description: string;
  base_sharpe: number;
  stressed_sharpe: number;
  base_max_dd: number;
  stressed_max_dd: number;
  base_final_equity: number;
  stressed_final_equity: number;
  drawdown_expansion_pct: number;
  equity_erosion_pct: number;
  status: "PASS" | "DEGRADED" | "FAILED" | string;
  critical_findings: string[];
}

// Pillar 4: Dynamic Risk & Underwater Tracker
export interface UnderwaterTracker {
  current_drawdown_pct: number;
  current_underwater_bars: number;
  max_historical_drawdown_pct: number;
  max_historical_underwater_bars: number;
  is_at_high_water_mark: boolean;
  estimated_bars_to_recovery?: number;
  recovery_status: "PEAK" | "SHALLOW_DIP" | "DEEP_DRAWDOWN" | "CRITICAL_RECESSION" | string;
}

export interface PortfolioRiskSnapshot {
  as_of_ts: string;
  current_equity: number;
  high_water_mark: number;
  current_drawdown_pct: number;
  daily_drawdown_pct: number;
  distance_to_daily_limit_pct: number;
  distance_to_max_limit_pct: number;
  realized_vol_pct: number;
  vol_target_multiplier: number;
  suggested_risk_pct: number;
  underwater_state: UnderwaterTracker;
  concentration_risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
  correlation_notes: string;
  recommended_action: "NORMAL" | "TRIM_EXPOSURE" | "HALT" | string;
  summary: string;
}

// Pillar 5: Personal Cash Flow & Capital Planning
export interface CashFlowItem {
  name: string;
  amount: number;
  flow_type: "income" | "expense";
  frequency: "monthly" | "annual" | "one_time";
  is_fixed: boolean;
}

export interface DebtItem {
  name: string;
  balance: number;
  interest_rate_pct: number;
  minimum_payment: number;
}

export interface FinancialGoal {
  title: string;
  target_amount: number;
  current_savings: number;
  target_months: number;
}

export interface EmergencyRunwayResult {
  liquid_reserves: number;
  monthly_fixed_expenses: number;
  monthly_total_expenses: number;
  runway_months: number;
  health_status: "CRITICAL" | "ADEQUATE" | "ROBUST" | string;
  recommended_target_reserve: number;
  reserve_deficit_or_surplus: number;
}

export interface DebtPayoffComparison {
  strategy_name: string;
  total_interest_paid: number;
  months_to_debt_free: number;
  monthly_cash_freed_up: number;
  summary: string;
}

export interface CompoundProjectionYear {
  year: number;
  gross_contributions: number;
  gross_portfolio_value: number;
  net_after_tax_fee_value: number;
  annual_tax_drag: number;
  cumulative_drag_dollars: number;
}

export interface FinancialPlanOutput {
  plan_id: string;
  as_of_ts: string;
  total_monthly_income: number;
  total_monthly_expenses: number;
  monthly_net_cashflow: number;
  savings_rate_pct: number;
  emergency_runway: EmergencyRunwayResult;
  debt_payoff_scenarios: DebtPayoffComparison[];
  goal_projections: Array<Record<string, any>>;
  compound_tax_drag_projection: CompoundProjectionYear[];
  total_10yr_tax_fee_drag_pct: number;
  executive_summary: string;
  action_plan: string[];
  disclaimer: string;
}


