"""Multi-Agent Quantitative Committee Package

Integrates multi-agent hedge fund committee patterns into QuantEdge:
- Technicals Analyst
- Regime & Volatility Analyst
- Risk Manager
- Portfolio Manager / CIO
- Committee Orchestrator
"""
from core.agents.state import AgentState
from core.agents.orchestrator import CommitteeOrchestrator
from core.agents.technicals_agent import TechnicalsAgent
from core.agents.regime_agent import RegimeAgent
from core.agents.risk_agent import RiskAgent
from core.agents.portfolio_manager_agent import PortfolioManagerAgent

__all__ = [
    "AgentState",
    "CommitteeOrchestrator",
    "TechnicalsAgent",
    "RegimeAgent",
    "RiskAgent",
    "PortfolioManagerAgent",
]
