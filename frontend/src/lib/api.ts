import {
  User,
  Strategy,
  StrategyVersion,
  BacktestRun,
  Tearsheet,
  TradeItem,
  EquityPoint,
  StrategySpecOutput,
  BacktestCritiqueOutput,
  OHLCVBar,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let authToken: string | null = null;
let activeWorkspaceId: string | null = null;

export const setAuthToken = (token: string, workspaceId?: string) => {
  authToken = token;
  if (workspaceId) activeWorkspaceId = workspaceId;
};

export const getAuthToken = () => authToken;
export const getActiveWorkspaceId = () => activeWorkspaceId;

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  if (activeWorkspaceId) {
    headers["X-Workspace-Id"] = activeWorkspaceId;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errDetail = "API Request failed";
    try {
      const err = await res.json();
      errDetail = err.detail || JSON.stringify(err);
    } catch {
      errDetail = await res.text();
    }
    throw new Error(errDetail);
  }

  return res.json();
}

export const api = {
  // Auth
  register: (payload: { email: string; password: string; workspace_name?: string }) =>
    request<{ access_token: string; user_id: string; workspace_id: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user_id: string; workspace_id: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMe: () => request<User>("/auth/me"),

  // Strategies
  listStrategies: () => request<Strategy[]>("/strategies/"),

  createStrategy: (payload: {
    name: string;
    description?: string;
    strategy_type: string;
    initial_parameters?: Record<string, any>;
  }) =>
    request<Strategy>("/strategies/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createVersion: (strategyId: string, parameters: Record<string, any>) =>
    request<StrategyVersion>(`/strategies/${strategyId}/versions`, {
      method: "POST",
      body: JSON.stringify({ parameters }),
    }),

  listVersions: (strategyId: string) =>
    request<StrategyVersion[]>(`/strategies/${strategyId}/versions`),

  // Backtests
  launchBacktest: (payload: {
    strategy_version_id: string;
    symbol: string;
    timeframe: string;
    start_date?: string;
    end_date?: string;
    initial_capital: number;
    slippage_bps: number;
    commission_per_trade: number;
    spread_pips: number;
    risk_per_trade_pct: number;
  }) =>
    request<{ job_id: string; status: string; message: string }>("/backtests/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listRuns: () => request<BacktestRun[]>("/backtests/"),

  getRunStatus: (runId: string) =>
    request<{ id: string; status: string; error_message?: string; completed_at?: string }>(
      `/backtests/${runId}/status`
    ),

  getTearsheet: (runId: string) => request<Tearsheet>(`/backtests/${runId}/tearsheet`),

  getTrades: (runId: string) => request<TradeItem[]>(`/backtests/${runId}/trades`),

  getEquityCurve: (runId: string) => request<EquityPoint[]>(`/backtests/${runId}/equity`),

  // Market Data
  getBars: (symbol = "XAUUSD", timeframe = "1H", limit = 300) =>
    request<OHLCVBar[]>(`/data/bars?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`),

  // Grounded AI
  parseHypothesis: (prompt: string) =>
    request<StrategySpecOutput>("/ai/hypothesis-to-spec", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),

  critiqueBacktest: (runId: string) =>
    request<BacktestCritiqueOutput>(`/ai/critique-backtest/${runId}`, {
      method: "POST",
    }),

  // Multi-Agent Committee
  conveneCommittee: (payload: {
    symbol?: string;
    timeframe?: string;
    strategy_version_id?: string;
    backtest_run_id?: string;
    limit_bars?: number;
  }) =>
    request<import("@/types").CommitteeReviewOutput>("/ai/committee-review", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listCommitteeReports: (limit = 20) =>
    request<import("@/types").CommitteeReportSummary[]>(`/ai/committee-reports?limit=${limit}`),

  getCommitteeReport: (reportId: string) =>
    request<import("@/types").CommitteeReviewOutput>(`/ai/committee-reports/${reportId}`),

  // Billing
  getUsage: () => request<any>("/billing/usage"),
};
