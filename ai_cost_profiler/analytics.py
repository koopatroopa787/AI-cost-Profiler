"""Analytics and optimization suggestion engine."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .models import ExpensivePrompt, CostSummary, AgentCost, TaskCost
from .storage import SQLiteStorage
from .pricing import PricingEngine, PROVIDER_INFO


@dataclass
class OptimizationSuggestion:
    """A cost optimization suggestion."""
    type: str  # "model_switch", "prompt_optimization", "caching", "batching"
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    estimated_monthly_savings: float
    affected_agent: Optional[str] = None
    affected_task: Optional[str] = None
    current_model: Optional[str] = None
    suggested_model: Optional[str] = None


class Analytics:
    """Analytics and optimization engine."""

    def __init__(self, storage: SQLiteStorage, pricing: Optional[PricingEngine] = None):
        self.storage = storage
        self.pricing = pricing or PricingEngine()

    def get_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> CostSummary:
        """Get overall cost summary."""
        records = self.storage.get_records(
            start_time=start_time,
            end_time=end_time,
            limit=100000
        )

        if not records:
            return CostSummary()

        total_cost = sum(r.total_cost for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        count = len(records)

        return CostSummary(
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            request_count=count,
            avg_cost_per_request=total_cost / count if count > 0 else 0,
            avg_tokens_per_request=total_tokens / count if count > 0 else 0,
            time_range_start=start_time,
            time_range_end=end_time
        )

    def get_costs_by_agent(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AgentCost]:
        """Get cost breakdown by agent."""
        data = self.storage.get_costs_by_agent(start_time, end_time)
        return [
            AgentCost(
                agent=row["agent"],
                total_cost=row["total_cost"],
                total_tokens=row["total_tokens"],
                request_count=row["request_count"],
                avg_cost_per_request=row["avg_cost"]
            )
            for row in data
        ]

    def get_costs_by_task(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[TaskCost]:
        """Get cost breakdown by task."""
        data = self.storage.get_costs_by_task(start_time, end_time)
        return [
            TaskCost(
                task=row["task"],
                agent=row["agent"],
                total_cost=row["total_cost"],
                total_tokens=row["total_tokens"],
                request_count=row["request_count"],
                avg_cost_per_request=row["avg_cost"]
            )
            for row in data
        ]

    def get_costs_by_model(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by model with enriched provider info."""
        rows = self.storage.get_costs_by_model(start_time, end_time)
        result = []
        for row in rows:
            provider_key = row.get("provider", "custom")
            info = PROVIDER_INFO.get(provider_key, {"name": provider_key, "icon": "⚙️"})
            result.append({
                **row,
                "provider_name": info["name"],
                "provider_icon": info["icon"],
            })
        return result

    def get_costs_by_provider(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by provider."""
        rows = self.storage.get_costs_by_provider(start_time, end_time)
        result = []
        for row in rows:
            provider_key = row.get("provider", "custom")
            info = PROVIDER_INFO.get(provider_key, {"name": provider_key, "icon": "⚙️", "url": ""})
            result.append({
                **row,
                "provider_name": info["name"],
                "provider_icon": info["icon"],
                "provider_url": info.get("url", ""),
            })
        return result

    def get_hourly_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly cost trend for charting."""
        return self.storage.get_hourly_trend(hours=hours)

    def get_latency_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get latency statistics."""
        return self.storage.get_latency_stats(start_time, end_time)

    def get_user_costs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by user."""
        return self.storage.get_user_costs(start_time, end_time)

    def get_expensive_prompts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10
    ) -> List[ExpensivePrompt]:
        """Identify expensive prompts."""
        all_prompts = self.storage.get_expensive_prompts(start_time, end_time, limit=1000)

        if not all_prompts:
            return []

        avg_tokens = sum(p["avg_tokens"] for p in all_prompts) / len(all_prompts)

        expensive = self.storage.get_expensive_prompts(start_time, end_time, limit=limit)

        return [
            ExpensivePrompt(
                prompt_hash=p["prompt_hash"],
                prompt_preview=p["prompt_preview"] or "",
                avg_tokens=p["avg_tokens"],
                avg_cost=p["avg_cost"],
                call_count=p["call_count"],
                total_cost=p["total_cost"],
                agent=p["agent"],
                task=p["task"],
                model=p["model"],
                token_ratio_vs_avg=p["avg_tokens"] / avg_tokens if avg_tokens > 0 else 1.0
            )
            for p in expensive
        ]

    def get_optimization_suggestions(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[OptimizationSuggestion]:
        """Generate cost optimization suggestions."""
        suggestions = []

        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=30)

        records = self.storage.get_records(start_time=start_time, end_time=end_time, limit=10000)

        if not records:
            return suggestions

        # Analyse by model usage
        model_usage: Dict[str, Dict[str, Any]] = {}
        for r in records:
            if r.model not in model_usage:
                model_usage[r.model] = {
                    "total_cost": 0,
                    "count": 0,
                    "agents": set(),
                    "tasks": set()
                }
            model_usage[r.model]["total_cost"] += r.total_cost
            model_usage[r.model]["count"] += 1
            model_usage[r.model]["agents"].add(r.agent)
            model_usage[r.model]["tasks"].add(r.task)

        # Suggest cheaper model alternatives
        for model, usage in model_usage.items():
            alternatives = self.pricing.get_cheaper_alternatives(model)
            if alternatives and usage["total_cost"] > 10:
                best_alt = alternatives[0]
                monthly_cost = usage["total_cost"]
                projected_savings = monthly_cost * (best_alt["savings_percent"] / 100)

                if projected_savings > 5:
                    suggestions.append(OptimizationSuggestion(
                        type="model_switch",
                        priority="high" if projected_savings > 100 else "medium",
                        title=f"Switch from {model} to {best_alt['model']}",
                        description=(
                            f"You're spending ${monthly_cost:.2f} on {model}. "
                            f"Switching to {best_alt['model']} "
                            f"({PROVIDER_INFO.get(best_alt['provider'], {}).get('name', best_alt['provider'])}) "
                            f"could save ~{best_alt['savings_percent']:.0f}% "
                            f"(≈${projected_savings:.2f}/period)."
                        ),
                        estimated_monthly_savings=projected_savings,
                        current_model=model,
                        suggested_model=best_alt["model"]
                    ))

        # Identify expensive prompts
        expensive_prompts = self.get_expensive_prompts(start_time, end_time, limit=5)
        for prompt in expensive_prompts:
            if prompt.token_ratio_vs_avg > 2.0 and prompt.total_cost > 5:
                suggestions.append(OptimizationSuggestion(
                    type="prompt_optimization",
                    priority="high" if prompt.total_cost > 50 else "medium",
                    title=f"Optimize expensive prompt in {prompt.agent}/{prompt.task}",
                    description=(
                        f"This prompt uses {prompt.token_ratio_vs_avg:.1f}x more tokens than average. "
                        f"Total cost: ${prompt.total_cost:.2f} across {prompt.call_count} calls."
                    ),
                    estimated_monthly_savings=prompt.total_cost * 0.5,
                    affected_agent=prompt.agent,
                    affected_task=prompt.task
                ))

        # Suggest caching for repeated prompts
        repeated_prompts = [p for p in expensive_prompts if p.call_count > 10]
        for prompt in repeated_prompts[:3]:
            if prompt.avg_cost > 0.01:
                suggestions.append(OptimizationSuggestion(
                    type="caching",
                    priority="medium",
                    title=f"Cache repeated prompt in {prompt.agent}/{prompt.task}",
                    description=(
                        f"This prompt was called {prompt.call_count} times. "
                        f"Caching responses could eliminate up to 70% of those costs."
                    ),
                    estimated_monthly_savings=prompt.total_cost * 0.7,
                    affected_agent=prompt.agent,
                    affected_task=prompt.task
                ))

        # Suggest local/free alternatives for expensive providers
        provider_usage = self.storage.get_costs_by_provider(start_time, end_time)
        for prov in provider_usage:
            if prov["total_cost"] > 50 and prov["provider"] not in ("ollama", "custom"):
                suggestions.append(OptimizationSuggestion(
                    type="local_alternative",
                    priority="low",
                    title=f"Consider local Ollama models for {prov['provider']} workloads",
                    description=(
                        f"You spent ${prov['total_cost']:.2f} with "
                        f"{PROVIDER_INFO.get(prov['provider'], {}).get('name', prov['provider'])}. "
                        f"Self-hosted Ollama models (Llama 3, Mistral, DeepSeek-R1, etc.) "
                        f"are completely free for suitable tasks."
                    ),
                    estimated_monthly_savings=prov["total_cost"] * 0.3,
                ))

        suggestions.sort(key=lambda s: s.estimated_monthly_savings, reverse=True)
        return suggestions

    def get_realtime_stats(self) -> Dict[str, Any]:
        """Get real-time statistics for dashboard."""
        now = datetime.utcnow()

        hour_ago = now - timedelta(hours=1)
        hour_records = self.storage.get_records(start_time=hour_ago, limit=10000)
        hour_cost = sum(r.total_cost for r in hour_records)
        hour_requests = len(hour_records)

        day_ago = now - timedelta(hours=24)
        day_records = self.storage.get_records(start_time=day_ago, limit=100000)
        day_cost = sum(r.total_cost for r in day_records)
        day_requests = len(day_records)

        latest = self.storage.get_records(limit=20)

        latency = self.storage.get_latency_stats(start_time=day_ago)

        return {
            "last_hour": {
                "cost": round(hour_cost, 4),
                "requests": hour_requests,
                "avg_cost": round(hour_cost / hour_requests, 4) if hour_requests > 0 else 0
            },
            "last_24h": {
                "cost": round(day_cost, 4),
                "requests": day_requests,
                "avg_cost": round(day_cost / day_requests, 4) if day_requests > 0 else 0
            },
            "latency": {
                "avg_ms": round(latency.get("avg_ms") or 0, 0),
                "min_ms": latency.get("min_ms") or 0,
                "max_ms": latency.get("max_ms") or 0,
            },
            "latest_records": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat(),
                    "agent": r.agent,
                    "task": r.task,
                    "model": r.model,
                    "provider": r.provider.value,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "tokens": r.total_tokens,
                    "cost": round(r.total_cost, 6),
                    "latency_ms": r.latency_ms,
                }
                for r in latest
            ]
        }

