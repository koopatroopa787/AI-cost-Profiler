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
