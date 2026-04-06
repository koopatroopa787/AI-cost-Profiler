"""
Demo script to generate sample usage data for the AI Cost Profiler dashboard.

Run this while the dashboard is running to see real-time updates:
    python examples/demo.py
    python examples/demo.py --count 50 --delay 0.2
"""

import argparse
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_cost_profiler import CostTracker
from ai_cost_profiler.models import Provider

# ── ANSI colours ─────────────────────────────────────────────────────────────
R = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
GREEN = "\033[92m"; CYAN = "\033[96m"; YELLOW = "\033[93m"
RED = "\033[91m"; BLUE = "\033[94m"; MAGENTA = "\033[95m"; WHITE = "\033[97m"

# ── Sample data for realistic simulation ─────────────────────────────────────
AGENTS = [
    "customer_support", "code_reviewer", "document_summarizer",
    "data_analyst", "content_writer", "security_scanner",
    "rag_pipeline", "sql_agent",
]

TASKS = {
    "customer_support":    ["answer_question", "escalate_ticket", "sentiment_analysis", "draft_reply"],
    "code_reviewer":       ["review_pr", "suggest_fix", "explain_code", "detect_bugs"],
    "document_summarizer": ["summarize_doc", "extract_key_points", "generate_tldr", "translate"],
    "data_analyst":        ["query_data", "generate_report", "create_chart", "anomaly_detection"],
    "content_writer":      ["write_blog", "edit_content", "generate_outline", "seo_optimise"],
    "security_scanner":    ["scan_code", "audit_deps", "generate_report"],
    "rag_pipeline":        ["embed_chunk", "retrieve_context", "synthesise_answer"],
    "sql_agent":           ["natural_language_to_sql", "explain_query", "optimise_query"],
}

# Models across 10+ providers
MODELS = [
    # OpenAI
    ("gpt-4o",              Provider.OPENAI,      (500, 4000), (200, 2000)),
    ("gpt-4o-mini",         Provider.OPENAI,      (100, 1000), (50,  500)),
    ("gpt-4.1",             Provider.OPENAI,      (600, 5000), (250, 2500)),
    ("gpt-4.1-nano",        Provider.OPENAI,      (80,  800),  (40,  400)),
    ("o3-mini",             Provider.OPENAI,      (300, 3000), (100, 1500)),
    # Anthropic
    ("claude-3-5-sonnet",   Provider.ANTHROPIC,   (500, 4000), (200, 2000)),
    ("claude-3-5-haiku",    Provider.ANTHROPIC,   (100, 1000), (50,  500)),
    ("claude-3-opus",       Provider.ANTHROPIC,   (800, 6000), (400, 3000)),
    # Google
    ("gemini-2.5-pro",      Provider.GOOGLE,      (600, 5000), (300, 2500)),
    ("gemini-2.0-flash",    Provider.GOOGLE,      (100, 1000), (50,  500)),
    # Mistral
    ("mistral-large-2",     Provider.MISTRAL,     (400, 3000), (200, 1500)),
    ("mistral-small",       Provider.MISTRAL,     (100, 800),  (50,  400)),
    # DeepSeek
    ("deepseek-chat",       Provider.DEEPSEEK,    (200, 2000), (100, 1000)),
    ("deepseek-reasoner",   Provider.DEEPSEEK,    (400, 3000), (200, 1500)),
    # xAI
    ("grok-2",              Provider.XAI,         (400, 3000), (200, 1500)),
    # Groq
    ("llama-3.3-70b-versatile", Provider.GROQ,   (100, 800),  (50,  400)),
    ("llama-3.1-8b-instant",    Provider.GROQ,   (50,  500),  (25,  250)),
    # Together
    ("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", Provider.TOGETHER, (200, 1500), (100, 750)),
    # Cohere
    ("command-r-plus",      Provider.COHERE,      (400, 3000), (200, 1500)),
    ("command-r",           Provider.COHERE,      (100, 800),  (50,  400)),
    # Ollama / Local
    ("ollama/llama3.2",     Provider.OLLAMA,      (200, 2000), (100, 1000)),
    ("ollama/mistral",      Provider.OLLAMA,      (200, 2000), (100, 1000)),
]

PROMPTS = [
    "You are a helpful customer support agent. Please help the user.",
    "Review the following code and suggest improvements:",
    "Summarize the following document in 3-5 bullet points:",
    "Analyze the following data and provide insights:",
    "Write a blog post about the following topic:",
    "Explain this concept in simple terms:",
    "Generate a detailed report based on the following data:",
    "Create an outline for a presentation about:",
    "Translate this technical document for a non-technical audience:",
    "Identify security vulnerabilities in the following code:",
]

USERS = [f"user_{i:02d}" for i in range(1, 16)]


def _fmt_cost(val: float) -> str:
    if val == 0:
        return f"{GREEN}FREE      {R}"
    if val < 0.001:
        return f"{GREEN}${val:.8f}{R}"
    if val < 0.01:
        return f"{YELLOW}${val:.6f}{R}"
    return f"{RED}${val:.4f}    {R}"


def _progress_bar(current: int, total: int, width: int = 25) -> str:
    filled = int(current / total * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = current / total * 100
    colour = GREEN if pct < 50 else YELLOW if pct < 80 else CYAN
    return f"{colour}{bar}{R} {DIM}{pct:.0f}%{R}"


def print_banner():
    print(f"\n{CYAN}{'═' * 65}{R}")
    print(f"{BOLD}{CYAN}  ◈  AI COST PROFILER  ·  SIMULATION DEMO{R}")
    print(f"{CYAN}{'═' * 65}{R}\n")


def print_summary(tracker: CostTracker, count: int):
    summary = tracker.analytics.get_summary()
    print(f"\n{CYAN}{'─' * 65}{R}")
    print(f"{BOLD}  📊 SIMULATION SUMMARY{R}")
    print(f"{CYAN}{'─' * 65}{R}")
    print(f"  {BOLD}Total Requests:{R}  {CYAN}{summary.request_count:,}{R}")
    print(f"  {BOLD}Total Tokens:{R}    {CYAN}{summary.total_tokens:,}{R}")
    print(f"  {BOLD}  ↳ Input:{R}       {DIM}{summary.total_input_tokens:,}{R}")
    print(f"  {BOLD}  ↳ Output:{R}      {DIM}{summary.total_output_tokens:,}{R}")
    print(f"  {BOLD}Total Cost:{R}      {_fmt_cost(summary.total_cost)}")
    print(f"  {BOLD}Avg/Request:{R}     {_fmt_cost(summary.avg_cost_per_request)}")

    # By provider
    providers = tracker.analytics.get_costs_by_provider()
    if providers:
        print(f"\n  {BOLD}By Provider:{R}")
        for p in providers[:8]:
            icon = p.get("provider_icon", "⚙️")
            name = p.get("provider_name", p["provider"])
            print(f"    {icon} {CYAN}{name:<22}{R} {_fmt_cost(p['total_cost'])}  "
                  f"{DIM}{p['request_count']} reqs{R}")

    print(f"{CYAN}{'─' * 65}{R}\n")


def simulate_usage(tracker: CostTracker, count: int = 30, delay: float = 0.3):
    print_banner()
    print(f"  {GREEN}▶  Starting simulation of {BOLD}{count}{R}{GREEN} API calls{R}")
    print(f"  {DIM}Dashboard: http://127.0.0.1:8000{R}\n")
    print(f"  {BOLD}{'#':<5} {'Agent':<22} {'Model':<32} {'Tokens':>8}  Cost{R}")
    print(f"  {DIM}{'─' * 75}{R}")

    for i in range(count):
        agent = random.choice(AGENTS)
        task = random.choice(TASKS[agent])
        model_name, provider, in_range, out_range = random.choice(MODELS)
        user = random.choice(USERS)
        prompt = random.choice(PROMPTS)
        input_tokens = random.randint(*in_range)
        output_tokens = random.randint(*out_range)
        latency = random.randint(80, 4000)

        record = tracker.record(
            agent=agent,
            task=task,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider=provider,
            user=user,
            prompt=prompt,
            latency_ms=latency,
        )

        # Colour cost by magnitude
        cost_str = _fmt_cost(record.total_cost)
        tok_str = f"{record.total_tokens:,}"

        # Truncate model name for display
        model_display = model_name if len(model_name) <= 30 else model_name[:27] + "…"

        print(f"  {DIM}{i+1:<5}{R} {CYAN}{agent:<22}{R} "
              f"{WHITE}{model_display:<32}{R} "
              f"{DIM}{tok_str:>8}{R}  {cost_str}  "
              f"{DIM}{latency}ms{R}  "
              f"[{_progress_bar(i + 1, count, 15)}]")

        time.sleep(delay)

    print(f"\n  {GREEN}✅ Simulation complete!{R}")
    print_summary(tracker, count)

    # Suggestions
    suggestions = tracker.analytics.get_optimization_suggestions()
    if suggestions:
        print(f"  {BOLD}💡 Top Optimization Suggestions:{R}\n")
        for s in suggestions[:3]:
            priority_col = RED if s.priority == "high" else YELLOW if s.priority == "medium" else CYAN
            print(f"  {priority_col}▲ [{s.priority.upper()}]{R} {BOLD}{s.title}{R}")
            print(f"     {DIM}{s.description}{R}")
            print(f"     {GREEN}Save ~${s.estimated_monthly_savings:.2f}{R}\n")


def main():
    parser = argparse.ArgumentParser(description="AI Cost Profiler Demo")
    parser.add_argument("--count", type=int, default=30, help="Number of simulated API calls")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between calls (seconds)")
    parser.add_argument("--db", default="ai_costs.db", help="Database path")
    args = parser.parse_args()

    tracker = CostTracker(db_path=args.db)
    simulate_usage(tracker=tracker, count=args.count, delay=args.delay)


if __name__ == "__main__":
    main()

