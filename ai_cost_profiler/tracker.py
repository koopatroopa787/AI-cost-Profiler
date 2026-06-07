"""Main CostTracker class for instrumenting AI applications."""

import asyncio
import functools
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List

from .models import UsageRecord, Provider
from .pricing import PricingEngine
from .token_counter import TokenCounter, get_token_counter
from .storage import StorageBackend, SQLiteStorage
from .analytics import Analytics


class CostTracker:
    """
    Main class for tracking LLM costs in AI applications.
    
    Usage:
        tracker = CostTracker()
        
        # Decorator
        @tracker.track(agent="customer_support", task="answer_question")
        def my_agent():
            response = openai.chat.completions.create(...)
            return response
        
        # Context manager
        with tracker.track_context(agent="customer_support", task="answer_question"):
            response = openai.chat.completions.create(...)
        
        # Manual recording
        tracker.record(
            agent="customer_support",
            task="answer_question",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50
        )
    """
    
    def __init__(
        self,
        storage: Optional[StorageBackend] = None,
        pricing: Optional[PricingEngine] = None,
        db_path: str = "ai_costs.db",
        enable_realtime: bool = True
    ):
        self.storage = storage or SQLiteStorage(db_path)
        self.pricing = pricing or PricingEngine()
        self.token_counter = get_token_counter()
        self.enable_realtime = enable_realtime
        
        # Real-time callbacks for dashboard
        self._realtime_callbacks: List[Callable[[UsageRecord], None]] = []
        
        # Analytics
        self._analytics: Optional[Analytics] = None
    
    @property
    def analytics(self) -> Analytics:
        """Get analytics engine."""
        if self._analytics is None:
            self._analytics = Analytics(self.storage, self.pricing)
        return self._analytics
    
    def add_realtime_callback(self, callback: Callable[[UsageRecord], None]) -> None:
        """Add callback for real-time cost updates."""
        self._realtime_callbacks.append(callback)
    
    def remove_realtime_callback(self, callback: Callable[[UsageRecord], None]) -> None:
        """Remove a real-time callback."""
        if callback in self._realtime_callbacks:
            self._realtime_callbacks.remove(callback)
    
    def _notify_callbacks(self, record: UsageRecord) -> None:
        """Notify all real-time callbacks of a new record."""
        for callback in self._realtime_callbacks:
            try:
                callback(record)
            except Exception:
                pass  # Don't let callback errors affect tracking
    
    def record(
        self,
        agent: str,
        task: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Provider = Provider.OPENAI,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """
        Record a usage event.
        
        Args:
            agent: Name of the agent making the call
            task: Specific task being performed
            model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: LLM provider
            user: Optional user identifier
            prompt: Optional prompt text for analysis
            latency_ms: Optional response latency in milliseconds
        
        Returns:
            The created UsageRecord
        """
        # Calculate costs
        input_cost, output_cost, total_cost = self.pricing.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider
        )
        
        # Create hash and preview for prompt analysis
        prompt_hash = None
        prompt_preview = None
        if prompt:
            prompt_hash = self.token_counter.hash_prompt(prompt)
            prompt_preview = self.token_counter.get_prompt_preview(prompt)
        
        record = UsageRecord(
            agent=agent,
            task=task,
            user=user,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            prompt_hash=prompt_hash,
            prompt_preview=prompt_preview,
            latency_ms=latency_ms
        )
        
        # Save to storage
        self.storage.save(record)
        
        # Notify real-time listeners
        if self.enable_realtime:
            self._notify_callbacks(record)
        
        return record
    
    def record_openai_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from an OpenAI API response object."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "gpt-4o")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.OPENAI, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_anthropic_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from an Anthropic API response object."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "claude-3-5-sonnet")

        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.ANTHROPIC, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_google_response(
        self,
        response: Any,
        agent: str,
        task: str,
        model: str = "gemini-2.0-flash",
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Google Gemini API response object."""
        # Try to extract from usage_metadata (google-generativeai SDK)
        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        else:
            input_tokens = 0
            output_tokens = 0

        detected_model = getattr(response, "model", None) or model

        return self.record(
            agent=agent, task=task, model=detected_model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.GOOGLE, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_mistral_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Mistral API response object."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "mistral-large")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.MISTRAL, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_cohere_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Cohere API response object."""
        meta = getattr(response, "meta", None)
        tokens = getattr(meta, "tokens", None) if meta else None

        input_tokens = getattr(tokens, "input_tokens", 0) if tokens else 0
        output_tokens = getattr(tokens, "output_tokens", 0) if tokens else 0
        model = getattr(response, "model", "command-r")

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.COHERE, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_deepseek_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a DeepSeek API response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "deepseek-chat")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.DEEPSEEK, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_groq_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Groq API response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "llama-3.3-70b-versatile")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.GROQ, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_xai_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from an xAI (Grok) API response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "grok-2")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.XAI, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_together_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Together AI response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "meta-llama/Llama-3.3-70B-Instruct-Turbo")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.TOGETHER, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_perplexity_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Perplexity Sonar API response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "sonar")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.PERPLEXITY, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_fireworks_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from a Fireworks AI response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "accounts/fireworks/models/llama-v3p1-70b-instruct")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.FIREWORKS, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def record_openrouter_response(
        self,
        response: Any,
        agent: str,
        task: str,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """Record usage from an OpenRouter API response (OpenAI-compatible format)."""
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "openrouter/auto")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=Provider.OPENROUTER, user=user, prompt=prompt, latency_ms=latency_ms
        )

    def estimate_cost_from_text(
        self,
        input_text: str,
        model: str,
        estimated_output_tokens: int = 500,
        provider: Provider = Provider.OPENAI,
    ) -> Dict[str, Any]:
        """
        Estimate the cost of an API call before making it.

        Counts tokens in the input text, then calculates expected cost using
        the model's pricing. Useful for budget checks before sending large prompts.

        Args:
            input_text: The prompt text to estimate cost for.
            model: The model name to use for pricing lookup.
            estimated_output_tokens: Expected number of output tokens (default 500).
            provider: The provider enum for fallback pricing.

        Returns:
            A dict with keys: input_tokens, estimated_output_tokens,
            input_cost, output_cost, total_cost, model, currency.
        """
        input_tokens = self.token_counter.count_tokens(input_text)
        input_cost, output_cost, total_cost = self.pricing.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=estimated_output_tokens,
            provider=provider,
        )
        return {
            "model": model,
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "input_cost": round(input_cost, 8),
            "output_cost": round(output_cost, 8),
            "total_cost": round(total_cost, 8),
            "currency": "USD",
        }

    def record_generic_openai_compatible(
        self,
        response: Any,
        agent: str,
        task: str,
        provider: Provider = Provider.CUSTOM,
        user: Optional[str] = None,
        prompt: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> UsageRecord:
        """
        Record usage from any OpenAI-compatible API response.

        Works with Groq, Together AI, xAI, DeepSeek, Perplexity, Fireworks,
        Azure OpenAI, and any other provider using the OpenAI response format.
        """
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", "unknown")

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        return self.record(
            agent=agent, task=task, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            provider=provider, user=user, prompt=prompt, latency_ms=latency_ms
        )
    
    def track(
        self,
        agent: str,
        task: str,
        provider: Provider = Provider.OPENAI,
        user: Optional[str] = None
    ) -> Callable:
        """
        Decorator for tracking LLM calls in a function.

        The decorated function should return an API response object with a
        `usage` attribute for automatic token extraction. Works with OpenAI,
        Anthropic, Google, Mistral, DeepSeek, Groq, xAI, Together AI, and
        any other OpenAI-compatible provider.
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                latency_ms = int((time.time() - start_time) * 1000)
                self._record_from_response(result, agent, task, provider, user, latency_ms)
                return result

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                result = await func(*args, **kwargs)
                latency_ms = int((time.time() - start_time) * 1000)
                self._record_from_response(result, agent, task, provider, user, latency_ms)
                return result

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return wrapper

        return decorator

    def _record_from_response(
        self,
        result: Any,
        agent: str,
        task: str,
        provider: Provider,
        user: Optional[str],
        latency_ms: int
    ) -> Optional[UsageRecord]:
        """Auto-detect and record from any supported API response format."""
        if not hasattr(result, "usage") and not hasattr(result, "usage_metadata"):
            return None

        if provider == Provider.ANTHROPIC:
            return self.record_anthropic_response(result, agent, task, user=user, latency_ms=latency_ms)
        elif provider == Provider.GOOGLE:
            return self.record_google_response(result, agent, task, user=user, latency_ms=latency_ms)
        elif provider == Provider.COHERE:
            return self.record_cohere_response(result, agent, task, user=user, latency_ms=latency_ms)
        else:
            # All OpenAI-compatible providers (OpenAI, DeepSeek, Groq, xAI, Together, Mistral, etc.)
            return self.record_generic_openai_compatible(result, agent, task, provider, user=user, latency_ms=latency_ms)
    
    @contextmanager
    def track_context(
        self,
        agent: str,
        task: str,
        model: str = "gpt-4o",
        provider: Provider = Provider.OPENAI,
        user: Optional[str] = None
    ):
        """
        Context manager for manually tracking LLM calls.
        
        Usage:
            with tracker.track_context(agent="support", task="answer") as ctx:
                response = openai.chat.completions.create(...)
                ctx.record_response(response)
        """
        context = TrackingContext(
            tracker=self,
            agent=agent,
            task=task,
            model=model,
            provider=provider,
            user=user
        )
        context.start()
        try:
            yield context
        finally:
            context.stop()


class TrackingContext:
    """Context for manual tracking within a context manager."""
    
    def __init__(
        self,
        tracker: CostTracker,
        agent: str,
        task: str,
        model: str,
        provider: Provider,
        user: Optional[str]
    ):
        self.tracker = tracker
        self.agent = agent
        self.task = task
        self.model = model
        self.provider = provider
        self.user = user
        self.start_time: Optional[float] = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
    
    def stop(self):
        """Stop timing."""
        pass
    
    def get_latency_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)
    
    def record_response(self, response: Any, prompt: Optional[str] = None) -> UsageRecord:
        """Record a response within this context. Works with all supported providers."""
        latency_ms = self.get_latency_ms()
        return self.tracker._record_from_response(
            response, self.agent, self.task, self.provider, self.user, latency_ms
        ) or self.record_manual(0, 0, prompt)
    
    def record_manual(
        self,
        input_tokens: int,
        output_tokens: int,
        prompt: Optional[str] = None
    ) -> UsageRecord:
        """Manually record token usage."""
        return self.tracker.record(
            agent=self.agent,
            task=self.task,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=self.provider,
            user=self.user,
            prompt=prompt,
            latency_ms=self.get_latency_ms()
        )


# Global default tracker instance
_default_tracker: Optional[CostTracker] = None


def get_tracker(db_path: str = "ai_costs.db") -> CostTracker:
    """Get the default tracker instance."""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = CostTracker(db_path=db_path)
    return _default_tracker
