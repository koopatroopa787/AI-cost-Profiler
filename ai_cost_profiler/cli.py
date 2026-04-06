"""
Interactive terminal CLI for AI Cost Profiler.

Usage:
    python -m ai_cost_profiler.cli [command] [options]
    ai-cost [command] [options]   # if installed via pip
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ANSI colour codes
R = "\033[0m"           # reset
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_DARK = "\033[40m"

# Box-drawing
TL, TR, BL, BR = "╔", "╗", "╚", "╝"
H, V = "═", "║"
LT, RT, TT, BT, CR = "╠", "╣", "╦", "╩", "╬"


def _box(title: str, width: int = 70) -> str:
    inner = width - 2
    pad = (inner - len(title)) // 2
    title_line = f"{V} {' ' * pad}{BOLD}{CYAN}{title}{R} {' ' * (inner - pad - len(title) - 1)}{V}"
    return (
        f"{GREEN}{TL}{H * inner}{TR}{R}\n"
        f"{title_line}\n"
        f"{GREEN}{BL}{H * inner}{BR}{R}"
    )


def _header_banner():
    lines = [
        r"  █████╗ ██╗      ██████╗ ██████╗ ███████╗████████╗",
        r" ██╔══██╗██║     ██╔════╝██╔═══██╗██╔════╝╚══██╔══╝",
        r" ███████║██║     ██║     ██║   ██║███████╗   ██║   ",
        r" ██╔══██║██║     ██║     ██║   ██║╚════██║   ██║   ",
        r" ██║  ██║██║     ╚██████╗╚██████╔╝███████║   ██║   ",
        r" ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═════╝ ╚══════╝   ╚═╝   ",
        r"",
        r"  ██████╗ ██████╗  ██████╗ ███████╗██╗██╗     ███████╗██████╗",
        r" ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██║██║     ██╔════╝██╔══██╗",
        r" ██████╔╝██████╔╝██║   ██║█████╗  ██║██║     █████╗  ██████╔╝",
        r" ██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██║██║     ██╔══╝  ██╔══██╗",
        r" ██║     ██║  ██║╚██████╔╝██║     ██║███████╗███████╗██║  ██║",
        r" ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
    ]
    print()
    for line in lines:
        print(f"  {CYAN}{line}{R}")
    print(f"\n  {DIM}Universal AI Cost Tracking · 20+ Providers · 70+ Models{R}\n")


def _fmt_cost(val: float) -> str:
    if val == 0:
        return f"{GREEN}FREE{R}"
    if val < 0.001:
        return f"{GREEN}${val:.8f}{R}"
    if val < 1:
        return f"{YELLOW}${val:.6f}{R}"
    return f"{RED}${val:.4f}{R}"


def _fmt_tokens(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)


def _bar(fraction: float, width: int = 30) -> str:
    filled = int(fraction * width)
    bar = "█" * filled + "░" * (width - filled)
    colour = GREEN if fraction < 0.4 else YELLOW if fraction < 0.7 else RED
    return f"{colour}{bar}{R}"


def _divider(width: int = 70, char: str = "─") -> str:
    return f"{DIM}{char * width}{R}"


def _get_storage(db_path: str):
    from ai_cost_profiler.storage import SQLiteStorage
    return SQLiteStorage(db_path)


def _get_analytics(db_path: str):
    from ai_cost_profiler.analytics import Analytics
    from ai_cost_profiler.pricing import PricingEngine
    storage = _get_storage(db_path)
    return Analytics(storage, PricingEngine())


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_stats(args):
    """Show overall cost statistics."""
    analytics = _get_analytics(args.db)
    hours = args.hours
    start_time = datetime.utcnow() - timedelta(hours=hours)

    _header_banner()
    print(_box(f"📊  COST STATISTICS  ·  Last {hours}h"))
    print()

    summary = analytics.get_summary(start_time=start_time)
    lat = analytics.get_latency_stats(start_time=start_time)

    label_w = 30
    print(f"  {BOLD}{'Metric':<{label_w}}Value{R}")
    print(f"  {_divider(50)}")

    rows = [
        ("💰 Total Cost",          _fmt_cost(summary.total_cost)),
        ("📨 Total Requests",      f"{CYAN}{summary.request_count:,}{R}"),
        ("🔤 Total Tokens",        f"{CYAN}{_fmt_tokens(summary.total_tokens)}{R}"),
        ("  ↳ Input Tokens",       f"{DIM}{_fmt_tokens(summary.total_input_tokens)}{R}"),
        ("  ↳ Output Tokens",      f"{DIM}{_fmt_tokens(summary.total_output_tokens)}{R}"),
        ("📈 Avg Cost / Request",  _fmt_cost(summary.avg_cost_per_request)),
        ("📝 Avg Tokens / Request",f"{CYAN}{summary.avg_tokens_per_request:,.0f}{R}"),
        ("⚡ Avg Latency",         f"{CYAN}{lat.get('avg_ms') or 0:.0f} ms{R}" if lat else "—"),
        ("⚡ Min / Max Latency",   f"{GREEN}{lat.get('min_ms') or 0} ms{R} / {RED}{lat.get('max_ms') or 0} ms{R}" if lat else "—"),
    ]
    for label, value in rows:
        print(f"  {BOLD}{label:<{label_w}}{R}{value}")

    print()

    # By-agent breakdown
    agents = analytics.get_costs_by_agent(start_time=start_time)
    if agents:
        print(f"\n  {BOLD}Cost by Agent{R}")
        print(f"  {_divider(60)}")
        max_cost = max(a.total_cost for a in agents) or 1
        for a in agents[:8]:
            fraction = a.total_cost / max_cost
            bar = _bar(fraction, 20)
            print(f"  {CYAN}{a.agent:<22}{R} {bar} {_fmt_cost(a.total_cost)}"
                  f"  {DIM}{a.request_count} reqs  {_fmt_tokens(a.total_tokens)} tok{R}")

    # By-provider breakdown
    providers = analytics.get_costs_by_provider(start_time=start_time)
    if providers:
        print(f"\n  {BOLD}Cost by Provider{R}")
        print(f"  {_divider(60)}")
        max_cost = max(p["total_cost"] for p in providers) or 1
        for p in providers[:10]:
            fraction = p["total_cost"] / max_cost
            bar = _bar(fraction, 20)
            icon = p.get("provider_icon", "⚙️")
            name = p.get("provider_name", p["provider"])
            print(f"  {icon} {CYAN}{name:<20}{R} {bar} {_fmt_cost(p['total_cost'])}"
                  f"  {DIM}{p['request_count']} reqs  {p.get('model_count', 1)} models{R}")

    print()


def cmd_models(args):
    """List all known models and their pricing."""
    from ai_cost_profiler.pricing import PricingEngine, PROVIDER_INFO

    engine = PricingEngine()
    models = engine.list_models(provider=args.provider if args.provider else None)

    _header_banner()
    title = "🤖  MODEL CATALOG"
    if args.provider:
        info = PROVIDER_INFO.get(args.provider, {})
        title += f"  ·  {info.get('icon', '')} {info.get('name', args.provider)}"
    print(_box(title))
    print()

    # Group by provider
    from collections import defaultdict
    by_provider = defaultdict(list)
    for m in models:
        by_provider[m["provider"]].append(m)

    for provider_key, pmodels in sorted(by_provider.items()):
        info = PROVIDER_INFO.get(provider_key, {"name": provider_key, "icon": "⚙️"})
        print(f"  {info['icon']} {BOLD}{CYAN}{info['name']}{R}  {DIM}{info.get('url', '')}{R}")
        print(f"  {_divider(68)}")
        print(f"  {BOLD}{'Model':<45} {'Input/1M':>9} {'Output/1M':>10}  {'Context':>8}  Feat{R}")
        print(f"  {_divider(68)}")

        for m in pmodels:
            inp = f"${m['input_per_1m']:.4f}" if m['input_per_1m'] > 0 else "FREE"
            out = f"${m['output_per_1m']:.4f}" if m['output_per_1m'] > 0 else "FREE"
            ctx = f"{m['context_window'] // 1000}K" if m['context_window'] >= 1000 else (str(m['context_window']) if m['context_window'] > 0 else "?")
            feats = ""
            if m["supports_vision"]:
                feats += "👁"
            if m["supports_tools"]:
                feats += "🔧"

            inp_col = GREEN if m["input_per_1m"] == 0 else YELLOW if m["input_per_1m"] < 1 else RED
            name_col = WHITE
            print(f"  {name_col}{m['model']:<45}{R} {inp_col}{inp:>9}{R} {inp_col}{out:>10}{R}  {DIM}{ctx:>8}{R}  {feats}")
        print()


def cmd_suggestions(args):
    """Show cost optimization suggestions."""
    analytics = _get_analytics(args.db)
    hours = args.hours
    start_time = datetime.utcnow() - timedelta(hours=hours)

    _header_banner()
    print(_box("💡  OPTIMIZATION SUGGESTIONS"))
    print()

    suggestions = analytics.get_optimization_suggestions(start_time=start_time)

    if not suggestions:
        print(f"  {GREEN}✅ No optimization opportunities found — you're doing great!{R}\n")
        return

    icons = {
        "model_switch": "🔄",
        "prompt_optimization": "✏️",
        "caching": "💾",
        "batching": "📦",
        "local_alternative": "🏠",
    }
    priority_colours = {"high": RED, "medium": YELLOW, "low": CYAN}

    for i, s in enumerate(suggestions[:10], 1):
        icon = icons.get(s.type, "💡")
        pcol = priority_colours.get(s.priority, WHITE)
        print(f"  {icon} {BOLD}{WHITE}[{i}] {s.title}{R}")
        print(f"      {DIM}{pcol}▲ {s.priority.upper()} PRIORITY{R}  "
              f"{GREEN}Save ~${s.estimated_monthly_savings:.2f}{R}")
        print(f"      {s.description}")
        if s.current_model:
            print(f"      {DIM}Current: {RED}{s.current_model}{R}  →  "
                  f"Suggested: {GREEN}{s.suggested_model}{R}")
        print()


def cmd_trend(args):
    """Show hourly cost trend."""
    analytics = _get_analytics(args.db)
    hours = args.hours

    _header_banner()
    print(_box(f"📈  COST TREND  ·  Last {hours}h"))
    print()

    rows = analytics.get_hourly_trend(hours=hours)

    if not rows:
        print(f"  {DIM}No data for this period.{R}\n")
        return

    max_cost = max(r["total_cost"] for r in rows) or 1
    max_reqs = max(r["request_count"] for r in rows) or 1

    print(f"  {BOLD}{'Hour (UTC)':<22} {'Cost':>10}  {'Requests':>9}  Trend{R}")
    print(f"  {_divider(68)}")
    for row in rows:
        hour = row["hour"][:16].replace("T", " ")
        cost_bar = _bar(row["total_cost"] / max_cost, 20)
        print(f"  {DIM}{hour}{R}  {_fmt_cost(row['total_cost']):>10}  "
              f"{CYAN}{row['request_count']:>9}{R}  {cost_bar}")
    print()


def cmd_live(args):
    """Tail live activity from the database."""
    from ai_cost_profiler.storage import SQLiteStorage
    import time

    storage = SQLiteStorage(args.db)

    _header_banner()
    print(_box("⚡  LIVE ACTIVITY FEED"))
    print()
    print(f"  {DIM}Watching {args.db} · Ctrl+C to stop{R}\n")
    print(f"  {BOLD}{'Time':<10} {'Agent':<20} {'Model':<30} {'Tokens':>8}  Cost{R}")
    print(f"  {_divider(80)}")

    seen_ids: set = set()
    try:
        while True:
            recent = storage.get_records(
                start_time=datetime.utcnow() - timedelta(minutes=5),
                limit=50
            )
            for r in reversed(recent):
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    t = r.timestamp.strftime("%H:%M:%S")
                    cost_col = GREEN if r.total_cost < 0.001 else YELLOW if r.total_cost < 0.1 else RED
                    lat = f"  {DIM}{r.latency_ms}ms{R}" if r.latency_ms else ""
                    print(f"  {DIM}{t}{R}  {CYAN}{r.agent:<20}{R}  "
                          f"{WHITE}{r.model:<30}{R}  "
                          f"{_fmt_tokens(r.total_tokens):>8}  "
                          f"{cost_col}${r.total_cost:.6f}{R}{lat}")
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n  {DIM}Stopped.{R}\n")


def cmd_dashboard(args):
    """Start the web dashboard."""
    import subprocess
    import sys

    port = args.port
    host = args.host
    print()
    print(_box(f"🖥   STARTING DASHBOARD  ·  http://{host}:{port}"))
    print()
    print(f"  {GREEN}▶  Dashboard URL:  {BOLD}http://{host}:{port}{R}")
    print(f"  {DIM}Press Ctrl+C to stop{R}\n")

    db_path = str(Path(args.db).resolve())
    env = os.environ.copy()
    env["AI_COST_DB"] = db_path

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "dashboard.app:app",
             "--host", host, "--port", str(port), "--reload"],
            cwd=str(Path(__file__).parent.parent),
            env=env,
        )
    except KeyboardInterrupt:
        print(f"\n  {DIM}Dashboard stopped.{R}\n")


def cmd_demo(args):
    """Run the demo simulation."""
    import subprocess
    import sys

    demo_path = Path(__file__).parent.parent / "examples" / "demo.py"
    subprocess.run([sys.executable, str(demo_path)] + (["--count", str(args.count)] if args.count else []))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="ai-cost",
        description=f"{BOLD}{CYAN}AI Cost Profiler CLI{R} — Universal AI cost tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Commands:{R}
  stats        Show cost statistics
  models       List all known AI models & pricing
  suggestions  Show cost optimization suggestions
  trend        Show hourly cost trend
  live         Tail live activity from the database
  dashboard    Start the web dashboard
  demo         Run demo simulation

{BOLD}Examples:{R}
  ai-cost stats --hours 24
  ai-cost models --provider openai
  ai-cost suggestions
  ai-cost live
  ai-cost dashboard --port 8080
        """
    )

    parser.add_argument("--db", default="ai_costs.db", metavar="PATH",
                        help="Path to the SQLite database (default: ai_costs.db)")
    parser.add_argument("--hours", type=int, default=24,
                        help="Time window in hours (default: 24)")

    subparsers = parser.add_subparsers(dest="command")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show cost statistics")
    p_stats.add_argument("--hours", type=int, default=24)
    p_stats.add_argument("--db", default="ai_costs.db")

    # models
    p_models = subparsers.add_parser("models", help="List all known AI models & pricing")
    p_models.add_argument("--provider", default=None,
                          help="Filter by provider key (e.g. openai, anthropic, groq)")

    # suggestions
    p_sugg = subparsers.add_parser("suggestions", help="Show optimization suggestions")
    p_sugg.add_argument("--hours", type=int, default=720)
    p_sugg.add_argument("--db", default="ai_costs.db")

    # trend
    p_trend = subparsers.add_parser("trend", help="Show hourly cost trend")
    p_trend.add_argument("--hours", type=int, default=24)
    p_trend.add_argument("--db", default="ai_costs.db")

    # live
    p_live = subparsers.add_parser("live", help="Tail live activity")
    p_live.add_argument("--db", default="ai_costs.db")

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="Start the web dashboard")
    p_dash.add_argument("--host", default="127.0.0.1")
    p_dash.add_argument("--port", type=int, default=8000)
    p_dash.add_argument("--db", default="ai_costs.db")

    # demo
    p_demo = subparsers.add_parser("demo", help="Run demo simulation")
    p_demo.add_argument("--count", type=int, default=None)

    args = parser.parse_args()

    command_map = {
        "stats":       cmd_stats,
        "models":      cmd_models,
        "suggestions": cmd_suggestions,
        "trend":       cmd_trend,
        "live":        cmd_live,
        "dashboard":   cmd_dashboard,
        "demo":        cmd_demo,
    }

    if args.command in command_map:
        # Propagate top-level --db/--hours if sub-command didn't set them
        if not hasattr(args, "db"):
            args.db = "ai_costs.db"
        if not hasattr(args, "hours"):
            args.hours = 24
        command_map[args.command](args)
    else:
        _header_banner()
        parser.print_help()
        print()


if __name__ == "__main__":
    main()
