"""
AI Cost Profiler - Lightweight SDK for tracking LLM costs in AI agent applications.

Usage:
    from ai_cost_profiler import CostTracker

    tracker = CostTracker()

    @tracker.track(agent="support_agent", task="answer_question")
    def my_agent_function():
        # Your LLM call here
        pass

    # Or use context manager
    with tracker.track_context(agent="support_agent", task="answer_question"):
        # Your LLM call here
        pass
"""

__version__ = "0.1.0"

from .tracker import CostTracker
from .models import UsageRecord, CostSummary, AgentCost, TaskCost
from .pricing import PricingEngine, Provider
from .token_counter import TokenCounter
from .storage import StorageBackend, SQLiteStorage
from .analytics import Analytics, OptimizationSuggestion

__all__ = [
    "CostTracker",
    "UsageRecord",
    "CostSummary",
    "AgentCost",
    "TaskCost",
    "PricingEngine",
    "Provider",
    "TokenCounter",
    "StorageBackend",
    "SQLiteStorage",
    "Analytics",
    "OptimizationSuggestion",
]
