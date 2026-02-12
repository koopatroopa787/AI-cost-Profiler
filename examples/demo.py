"""
Demo script to generate sample usage data for the AI Cost Profiler dashboard.

Run this while the dashboard is running to see real-time updates.
"""

import random
import time
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_cost_profiler import CostTracker
from ai_cost_profiler.models import Provider


# Sample data for realistic simulation
AGENTS = [
    "customer_support",
    "code_reviewer",
    "document_summarizer",
    "data_analyst",
    "content_writer"
]

TASKS = {
    "customer_support": ["answer_question", "escalate_ticket", "sentiment_analysis"],
    "code_reviewer": ["review_pr", "suggest_fix", "explain_code"],
    "document_summarizer": ["summarize_doc", "extract_key_points", "generate_tldr"],
    "data_analyst": ["query_data", "generate_report", "create_chart"],
    "content_writer": ["write_blog", "edit_content", "generate_outline"]
}

MODELS = [
    ("gpt-4o", Provider.OPENAI),
    ("gpt-4o-mini", Provider.OPENAI),
    ("gpt-3.5-turbo", Provider.OPENAI),
    ("claude-3-5-sonnet", Provider.ANTHROPIC),
    ("claude-3-5-haiku", Provider.ANTHROPIC),
    ("claude-3-haiku", Provider.ANTHROPIC),
]

PROMPTS = [
    "You are a helpful customer support agent. Please help the user with their question about our product.",
    "Review the following code and suggest improvements:",
    "Summarize the following document in 3-5 bullet points:",
    "Analyze the following data and provide insights:",
    "Write a blog post about the following topic:",
    "Please explain the following concept in simple terms:",
    "Generate a detailed report based on the following data:",
    "Create an outline for a presentation about:",
]

USERS = [f"user_{i}" for i in range(1, 11)]


def simulate_usage(tracker: CostTracker, count: int = 50, delay: float = 0.5):
    """Simulate realistic AI agent usage."""
    
    print(f"🚀 Starting simulation of {count} API calls...")
    print(f"📊 Dashboard: http://127.0.0.1:8000")
    print("-" * 50)
    
    for i in range(count):
        # Pick random agent and task
        agent = random.choice(AGENTS)
        task = random.choice(TASKS[agent])
        model, provider = random.choice(MODELS)
        user = random.choice(USERS)
        prompt = random.choice(PROMPTS)
        
        # Simulate token counts (realistic ranges)
        if "gpt-4" in model or "claude-3-5-sonnet" in model:
            # More expensive models used for complex tasks
            input_tokens = random.randint(500, 4000)
            output_tokens = random.randint(200, 2000)
        elif "haiku" in model or "mini" in model:
            # Cheaper models for simpler tasks  
            input_tokens = random.randint(100, 1000)
            output_tokens = random.randint(50, 500)
        else:
            input_tokens = random.randint(200, 2000)
            output_tokens = random.randint(100, 1000)
        
        # Record the usage
        record = tracker.record(
            agent=agent,
            task=task,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            user=user,
            prompt=prompt,
            latency_ms=random.randint(100, 3000)
        )
        
        print(f"[{i+1}/{count}] {agent}/{task} - {model}")
        print(f"         Tokens: {record.total_tokens:,} | Cost: ${record.total_cost:.6f}")
        
        time.sleep(delay)
    
    print("-" * 50)
    print("✅ Simulation complete!")
    
    # Print summary
    summary = tracker.analytics.get_summary()
    print(f"\n📈 SUMMARY")
    print(f"   Total Cost: ${summary.total_cost:.4f}")
    print(f"   Total Tokens: {summary.total_tokens:,}")
    print(f"   Total Requests: {summary.request_count}")
    print(f"   Avg Cost/Request: ${summary.avg_cost_per_request:.6f}")


def main():
    """Run the demo."""
    tracker = CostTracker(db_path="ai_costs.db")
    
    print("\n" + "=" * 50)
    print("  AI COST PROFILER - DEMO")
    print("=" * 50 + "\n")
    
    # Run simulation
    simulate_usage(
        tracker=tracker,
        count=30,  # Number of simulated API calls
        delay=0.3  # Delay between calls (seconds)
    )
    
    # Show suggestions
    print("\n💡 OPTIMIZATION SUGGESTIONS:")
    suggestions = tracker.analytics.get_optimization_suggestions()
    for s in suggestions[:3]:
        print(f"\n   [{s.priority.upper()}] {s.title}")
        print(f"   {s.description}")
        print(f"   Est. Savings: ${s.estimated_monthly_savings:.2f}/month")


if __name__ == "__main__":
    main()
