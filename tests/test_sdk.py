"""Tests for the AI Cost Profiler SDK."""

import pytest
from datetime import datetime, timedelta

from ai_cost_profiler import CostTracker
from ai_cost_profiler.models import UsageRecord, Provider
from ai_cost_profiler.pricing import PricingEngine, ModelPricing
from ai_cost_profiler.token_counter import TokenCounter
from ai_cost_profiler.storage import InMemoryStorage


class TestPricingEngine:
    """Tests for the pricing engine."""
    
    def test_calculate_cost_gpt4o(self):
        engine = PricingEngine()
        input_cost, output_cost, total = engine.calculate_cost(
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500
        )
        
        # GPT-4o: $2.50/1M input, $10.00/1M output
        assert input_cost == pytest.approx(0.0025, rel=0.01)
        assert output_cost == pytest.approx(0.005, rel=0.01)
        assert total == pytest.approx(0.0075, rel=0.01)
    
    def test_calculate_cost_claude(self):
        engine = PricingEngine()
        input_cost, output_cost, total = engine.calculate_cost(
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            provider=Provider.ANTHROPIC
        )
        
        # Claude 3.5 Sonnet: $3.00/1M input, $15.00/1M output
        assert input_cost == pytest.approx(0.003, rel=0.01)
        assert output_cost == pytest.approx(0.0075, rel=0.01)
    
    def test_fuzzy_model_matching(self):
        engine = PricingEngine()
        
        # Should match versioned model to base model
        pricing = engine.get_model_pricing("gpt-4o-2024-08-06")
        assert pricing is not None
        assert pricing.input_price == 2.50
    
    def test_custom_pricing(self):
        engine = PricingEngine()
        engine.add_custom_pricing("custom-model", 1.0, 2.0)
        
        input_cost, output_cost, total = engine.calculate_cost(
            model="custom-model",
            input_tokens=1000000,
            output_tokens=1000000
        )
        
        assert input_cost == 1.0
        assert output_cost == 2.0
    
    def test_cheaper_alternatives(self):
        engine = PricingEngine()
        alternatives = engine.get_cheaper_alternatives("gpt-4")
        
        assert len(alternatives) > 0
        # First alternative should have highest savings
        assert alternatives[0]["savings_percent"] > 0


class TestNewModels2026:
    """Tests for models added in the June 2026 pricing update."""

    def test_llama4_scout_groq(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("meta-llama/llama-4-scout-17b-16e-instruct")
        assert pricing is not None
        assert pricing.provider == "groq"
        assert pricing.input_price == pytest.approx(0.11)
        assert pricing.output_price == pytest.approx(0.34)
        assert pricing.supports_vision is True

    def test_llama4_maverick_groq(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("meta-llama/llama-4-maverick-17b-128e-instruct")
        assert pricing is not None
        assert pricing.provider == "groq"
        assert pricing.input_price == pytest.approx(0.50)
        assert pricing.supports_vision is True

    def test_llama4_scout_together(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("meta-llama/Llama-4-Scout-17B-16E-Instruct-Turbo")
        assert pricing is not None
        assert pricing.provider == "together"
        assert pricing.input_price == pytest.approx(0.18)
        assert pricing.output_price == pytest.approx(0.59)

    def test_llama4_base_meta(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("llama-4-scout")
        assert pricing is not None
        assert pricing.provider == "meta"
        assert pricing.context_window == 131_072

    def test_mistral_small_3_1(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("mistral-small-3.1")
        assert pricing is not None
        assert pricing.provider == "mistral"
        assert pricing.input_price == pytest.approx(0.10)
        assert pricing.output_price == pytest.approx(0.30)
        assert pricing.supports_vision is True

    def test_mistral_medium_3(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("mistral-medium-3")
        assert pricing is not None
        assert pricing.provider == "mistral"
        assert pricing.input_price == pytest.approx(0.40)
        assert pricing.output_price == pytest.approx(2.00)

    def test_amazon_nova_premier(self):
        engine = PricingEngine()
        pricing = engine.get_model_pricing("amazon.nova-premier-v1")
        assert pricing is not None
        assert pricing.provider == "amazon"
        assert pricing.input_price == pytest.approx(2.50)
        assert pricing.output_price == pytest.approx(12.50)
        assert pricing.supports_vision is True

    def test_nova_premier_more_expensive_than_nova_pro(self):
        engine = PricingEngine()
        premier = engine.get_model_pricing("amazon.nova-premier-v1")
        pro = engine.get_model_pricing("amazon.nova-pro-v1")
        assert premier.input_price > pro.input_price

    def test_llama4_cost_calculation(self):
        engine = PricingEngine()
        input_cost, output_cost, total = engine.calculate_cost(
            model="llama-4-scout",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        assert input_cost == pytest.approx(0.18, rel=0.01)
        assert output_cost == pytest.approx(0.295, rel=0.01)
        assert total == pytest.approx(0.475, rel=0.01)


class TestTokenCounter:
    """Tests for the token counter."""
    
    def test_count_tokens(self):
        counter = TokenCounter()
        
        # Simple test
        text = "Hello, world!"
        tokens = counter.count_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be less than characters
    
    def test_empty_text(self):
        counter = TokenCounter()
        assert counter.count_tokens("") == 0
    
    def test_prompt_hash(self):
        counter = TokenCounter()
        
        hash1 = counter.hash_prompt("Hello, world!")
        hash2 = counter.hash_prompt("Hello,  world!")  # Extra space
        
        # Normalized hashes should be equal
        assert hash1 == hash2
    
    def test_prompt_preview(self):
        counter = TokenCounter()
        
        short_text = "Short text"
        long_text = "A" * 300
        
        assert counter.get_prompt_preview(short_text) == short_text
        assert len(counter.get_prompt_preview(long_text)) <= 203  # 200 + "..."


class TestInMemoryStorage:
    """Tests for the in-memory storage backend."""
    
    def test_save_and_retrieve(self):
        storage = InMemoryStorage()
        
        record = UsageRecord(
            agent="test_agent",
            task="test_task",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50
        )
        
        storage.save(record)
        records = storage.get_records()
        
        assert len(records) == 1
        assert records[0].agent == "test_agent"
    
    def test_filter_by_agent(self):
        storage = InMemoryStorage()
        
        storage.save(UsageRecord(agent="agent1", task="task", model="gpt-4o", input_tokens=100, output_tokens=50))
        storage.save(UsageRecord(agent="agent2", task="task", model="gpt-4o", input_tokens=100, output_tokens=50))
        
        records = storage.get_records(agent="agent1")
        assert len(records) == 1
        assert records[0].agent == "agent1"
    
    def test_get_total_cost(self):
        storage = InMemoryStorage()
        
        storage.save(UsageRecord(
            agent="agent", task="task", model="gpt-4o",
            input_tokens=100, output_tokens=50,
            total_cost=0.10
        ))
        storage.save(UsageRecord(
            agent="agent", task="task", model="gpt-4o",
            input_tokens=100, output_tokens=50,
            total_cost=0.20
        ))
        
        total = storage.get_total_cost()
        assert total == pytest.approx(0.30)


class TestCostTracker:
    """Tests for the main CostTracker class."""
    
    def test_record_usage(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)
        
        record = tracker.record(
            agent="support",
            task="answer",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500
        )
        
        assert record.agent == "support"
        assert record.task == "answer"
        assert record.total_tokens == 1500
        assert record.total_cost > 0
    
    def test_record_with_prompt(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)
        
        record = tracker.record(
            agent="support",
            task="answer",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            prompt="Hello, how can I help you today?"
        )
        
        assert record.prompt_hash is not None
        assert record.prompt_preview is not None
    
    def test_realtime_callback(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)
        
        received = []
        
        def callback(record):
            received.append(record)
        
        tracker.add_realtime_callback(callback)
        
        tracker.record(
            agent="test",
            task="test",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50
        )
        
        assert len(received) == 1
        assert received[0].agent == "test"
    
    def test_decorator(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)
        
        # Create a mock response object
        class MockUsage:
            prompt_tokens = 100
            completion_tokens = 50
        
        class MockResponse:
            usage = MockUsage()
            model = "gpt-4o"
        
        @tracker.track(agent="decorator_test", task="test_task")
        def my_function():
            return MockResponse()
        
        result = my_function()
        
        # Check that usage was recorded
        records = storage.get_records()
        assert len(records) == 1
        assert records[0].agent == "decorator_test"


class TestNewTrackerMethods:
    """Tests for newly added tracker helper methods."""

    def test_record_perplexity_response(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)

        class MockUsage:
            prompt_tokens = 200
            completion_tokens = 100

        class MockResponse:
            usage = MockUsage()
            model = "sonar-pro"

        record = tracker.record_perplexity_response(
            MockResponse(), agent="search_bot", task="web_search"
        )

        assert record.provider == Provider.PERPLEXITY
        assert record.model == "sonar-pro"
        assert record.input_tokens == 200
        assert record.output_tokens == 100
        assert record.total_cost > 0

    def test_record_fireworks_response(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)

        class MockUsage:
            prompt_tokens = 150
            completion_tokens = 75

        class MockResponse:
            usage = MockUsage()
            model = "accounts/fireworks/models/llama-v3p1-70b-instruct"

        record = tracker.record_fireworks_response(
            MockResponse(), agent="fw_bot", task="chat"
        )

        assert record.provider == Provider.FIREWORKS
        assert record.model == "accounts/fireworks/models/llama-v3p1-70b-instruct"
        assert record.input_tokens == 150
        assert record.output_tokens == 75
        assert record.total_cost > 0

    def test_record_openrouter_response(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)

        class MockUsage:
            prompt_tokens = 80
            completion_tokens = 40

        class MockResponse:
            usage = MockUsage()
            model = "openrouter/auto"

        record = tracker.record_openrouter_response(
            MockResponse(), agent="router_bot", task="chat"
        )

        assert record.provider == Provider.OPENROUTER
        assert record.model == "openrouter/auto"
        assert record.input_tokens == 80
        assert record.output_tokens == 40
        assert record.total_cost > 0

    def test_estimate_cost_from_text_returns_expected_keys(self):
        tracker = CostTracker()
        estimate = tracker.estimate_cost_from_text(
            input_text="Hello, world!",
            model="gpt-4o",
            estimated_output_tokens=100,
        )

        assert "input_tokens" in estimate
        assert "estimated_output_tokens" in estimate
        assert "input_cost" in estimate
        assert "output_cost" in estimate
        assert "total_cost" in estimate
        assert "currency" in estimate
        assert estimate["currency"] == "USD"
        assert estimate["model"] == "gpt-4o"

    def test_estimate_cost_from_text_token_count(self):
        tracker = CostTracker()
        short = tracker.estimate_cost_from_text("Hi", "gpt-4o", 0)
        long = tracker.estimate_cost_from_text("Hello " * 100, "gpt-4o", 0)
        assert long["input_tokens"] > short["input_tokens"]

    def test_estimate_cost_from_text_total_equals_sum(self):
        tracker = CostTracker()
        estimate = tracker.estimate_cost_from_text(
            "Test prompt for cost estimation.",
            model="gpt-4o",
            estimated_output_tokens=200,
        )
        assert estimate["total_cost"] == pytest.approx(
            estimate["input_cost"] + estimate["output_cost"], rel=1e-6
        )

    def test_estimate_cost_from_text_expensive_model_costs_more(self):
        tracker = CostTracker()
        cheap = tracker.estimate_cost_from_text("Same prompt", "gpt-4o-mini", 100)
        expensive = tracker.estimate_cost_from_text("Same prompt", "gpt-4", 100)
        assert expensive["total_cost"] > cheap["total_cost"]


class TestAnalytics:
    """Tests for the analytics engine."""
    
    def test_get_summary(self):
        storage = InMemoryStorage()
        tracker = CostTracker(storage=storage)
        
        for i in range(10):
            tracker.record(
                agent=f"agent_{i % 3}",
                task="task",
                model="gpt-4o",
                input_tokens=100,
                output_tokens=50
            )
        
        summary = tracker.analytics.get_summary()
        
        assert summary.request_count == 10
        assert summary.total_cost > 0
        assert summary.avg_cost_per_request > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
