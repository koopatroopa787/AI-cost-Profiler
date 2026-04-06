# AI Cost Profiler

**Universal AI cost tracking SDK for Python — instrument any AI agent in minutes, track spending across 20+ providers and 70+ models in real-time.**

> "Your customer support agent just spent $47 in 10 minutes — switch it to Claude Haiku and save $2K/month."

---

## ✨ Features

- 🌐 **Universal compatibility** — 20+ providers, 70+ models tracked out of the box
- 💰 **Accurate cost calculation** per request, agent, task, user, model, and provider
- 📊 **Interactive web dashboard** with Chart.js charts, tabs, live feed, and model catalog
- ⚡ **Real-time WebSocket feed** — see every API call as it happens
- 🔍 **Expensive prompt detection** — find prompts consuming 3× more tokens than average
- 💡 **AI-powered optimization suggestions** — model-switch, caching, prompt compression
- 🔄 **Hourly cost trend charts** — visualize spending over time
- 🤖 **Full model catalog** — searchable, sortable table of every known AI model + pricing
- 🖥️ **Interactive CLI** with ANSI art, coloured output, live tail
- 🪶 **Zero-overhead** — adds < 1 ms to your API calls
- 🏠 **Ollama / local model support** — tracks free local models too
- 🔧 **No extra APIs needed** — all pricing data is bundled

---

## 📦 Installation

```bash
pip install -e .
```

### CLI entry point

After installation a `ai-cost` command is available:

```bash
ai-cost stats           # Show cost statistics
ai-cost models          # List all 70+ models with pricing
ai-cost suggestions     # Show optimization suggestions
ai-cost trend           # Show hourly cost trend
ai-cost live            # Tail live API activity
ai-cost dashboard       # Start web dashboard
ai-cost demo            # Run demo simulation
```

---

## 🚀 Quick Start

### Manual recording (any provider)

```python
from ai_cost_profiler import CostTracker, Provider

tracker = CostTracker()

tracker.record(
    agent="customer_support",
    task="answer_question",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500,
    provider=Provider.OPENAI,
    user="alice",
)
```

### Auto-record with decorator

```python
@tracker.track(agent="support_bot", task="chat", provider=Provider.OPENAI)
def chat(message: str):
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )

response = chat("Hello!")  # Cost recorded automatically
```

### Context manager

```python
with tracker.track_context(agent="analyst", task="summarize",
                            provider=Provider.ANTHROPIC) as ctx:
    response = anthropic_client.messages.create(...)
    ctx.record_response(response)
```

---

## 🌐 Supported Providers & Models

All pricing is bundled — no external API calls needed.

| Provider | Key | Example models |
|---|---|---|
| **OpenAI** | `openai` | gpt-4o, gpt-4.1, o3-mini, o1, gpt-4o-mini, gpt-4.1-nano |
| **Anthropic** | `anthropic` | claude-3-5-sonnet, claude-3-opus, claude-3-5-haiku |
| **Google** | `google` | gemini-2.5-pro, gemini-2.0-flash, gemini-1.5-pro |
| **Mistral AI** | `mistral` | mistral-large-2, codestral, mixtral-8x22b, mistral-nemo |
| **DeepSeek** | `deepseek` | deepseek-chat (V3), deepseek-reasoner (R1), deepseek-coder |
| **xAI (Grok)** | `xai` | grok-3, grok-3-mini, grok-2, grok-2-mini |
| **Cohere** | `cohere` | command-r-plus, command-r |
| **AI21 Labs** | `ai21` | jamba-1.5-large, jamba-1.5-mini |
| **Groq** | `groq` | llama-3.3-70b-versatile, llama-3.1-8b-instant |
| **Together AI** | `together` | Llama 3.3 70B, Llama 3.1 405B, Qwen 2.5 72B |
| **Perplexity** | `perplexity` | sonar-pro, sonar, llama-3.1-sonar-huge |
| **Meta (Llama)** | `meta` | llama-3.2-90b, llama-3.1-405b, llama-3.2-11b |
| **AWS Bedrock** | `amazon` | nova-pro, nova-lite, nova-micro, titan-text-express |
| **Fireworks AI** | `fireworks` | firefunction-v2, llama-v3p1-70b |
| **Ollama/Local** | `ollama` | llama3.2, mistral, gemma2, deepseek-r1, phi4 (FREE) |

> **70+ models** tracked in total. See full list: `ai-cost models`

### Provider helpers

```python
from ai_cost_profiler import CostTracker, Provider

tracker = CostTracker()

# OpenAI (auto-extracts from response object)
tracker.record_openai_response(response, agent="bot", task="chat")

# Anthropic
tracker.record_anthropic_response(response, agent="bot", task="summarize")

# Google Gemini
tracker.record_google_response(response, agent="bot", task="analyse",
                               model="gemini-2.5-pro")

# Mistral
tracker.record_mistral_response(response, agent="bot", task="code")

# Cohere
tracker.record_cohere_response(response, agent="bot", task="rag")

# DeepSeek / Groq / xAI / Together / any OpenAI-compatible
tracker.record_generic_openai_compatible(response, agent="bot", task="task",
                                         provider=Provider.GROQ)
```

---

## 📊 Dashboard

```bash
# Start the dashboard
python -m uvicorn dashboard.app:app --reload

# Or use the CLI
ai-cost dashboard --port 8000

# Open http://127.0.0.1:8000
```

### Dashboard tabs

| Tab | Content |
|---|---|
| **Overview** | Hourly cost trend chart, provider doughnut chart, suggestions, live feed |
| **Providers** | Cost bars, token usage, latency, links by provider |
| **Models** | Cost table per model + model share doughnut |
| **Agents** | Cost bars by agent + cost bars by task |
| **Prompts** | Top 10 most expensive prompt patterns |
| **Catalog** | Searchable / sortable table of all 70+ known models |

---

## 🔌 REST API Endpoints

All endpoints support a `?hours=N` query parameter (default 24).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/costs/summary` | Overall cost summary |
| `GET` | `/api/costs/by-agent` | Cost breakdown by agent |
| `GET` | `/api/costs/by-task` | Cost breakdown by task |
| `GET` | `/api/costs/by-model` | Cost breakdown by model |
| `GET` | `/api/costs/by-provider` | Cost breakdown by provider |
| `GET` | `/api/costs/trend` | Hourly cost trend for charts |
| `GET` | `/api/costs/expensive-prompts` | Top expensive prompt patterns |
| `GET` | `/api/costs/latency` | Latency statistics |
| `GET` | `/api/costs/by-user` | Cost breakdown by user |
| `GET` | `/api/suggestions` | AI-powered optimization suggestions |
| `GET` | `/api/models/catalog` | Full model catalog with pricing |
| `GET` | `/api/models/providers` | All supported providers |
| `POST` | `/api/record` | Record a usage event |
| `WS` | `/ws/live` | Real-time WebSocket updates |

---

## 💻 CLI Reference

```bash
# Cost statistics (last 24h by default)
ai-cost stats --hours 48 --db my_app.db

# List models (filter by provider)
ai-cost models --provider anthropic
ai-cost models --provider groq

# Optimization suggestions (last 30 days)
ai-cost suggestions --hours 720

# Hourly trend chart in terminal
ai-cost trend --hours 72

# Tail live activity (updates every second)
ai-cost live --db ai_costs.db

# Start web dashboard
ai-cost dashboard --host 0.0.0.0 --port 8080

# Run demo simulation
ai-cost demo --count 50 --delay 0.2
```

---

## 🔑 Custom Model Pricing

```python
from ai_cost_profiler import CostTracker

tracker = CostTracker()

# Add custom model pricing ($ per 1M tokens)
tracker.pricing.add_custom_pricing(
    model="my-fine-tuned-gpt4",
    input_price=5.00,
    output_price=15.00,
    provider="custom",
    description="My fine-tuned model"
)

tracker.record(
    agent="bot", task="chat",
    model="my-fine-tuned-gpt4",
    input_tokens=1000, output_tokens=500,
)
```

---

## 📈 Analytics API

```python
from ai_cost_profiler import CostTracker
from datetime import datetime, timedelta

tracker = CostTracker()
start = datetime.utcnow() - timedelta(days=7)

# Summary
summary = tracker.analytics.get_summary(start_time=start)
print(f"Total cost: ${summary.total_cost:.4f}")

# By provider
for p in tracker.analytics.get_costs_by_provider(start_time=start):
    print(f"{p['provider_name']}: ${p['total_cost']:.4f}")

# By model
for m in tracker.analytics.get_costs_by_model(start_time=start):
    print(f"{m['model']}: ${m['total_cost']:.4f}")

# Hourly trend
trend = tracker.analytics.get_hourly_trend(hours=48)

# Latency stats
lat = tracker.analytics.get_latency_stats(start_time=start)
print(f"Avg latency: {lat['avg_ms']:.0f} ms")

# Cheaper alternatives
alts = tracker.pricing.get_cheaper_alternatives("gpt-4o", top_n=3)
for a in alts:
    print(f"{a['model']} saves {a['savings_percent']:.0f}%")
```

---

## 📁 Project Structure

```
ai_cost_profiler/
├── __init__.py       # Package exports (v0.2.0)
├── tracker.py        # Main CostTracker class + provider helpers
├── models.py         # Data models + expanded Provider enum (21 providers)
├── pricing.py        # 70+ models with full metadata + PricingEngine
├── token_counter.py  # Token counting (tiktoken)
├── storage.py        # SQLite storage + by-model/provider/trend queries
├── analytics.py      # Analytics, suggestions, real-time stats
└── cli.py            # Interactive terminal CLI

dashboard/
├── app.py            # FastAPI server (20+ endpoints)
└── static/
    ├── index.html    # Dashboard UI with tabs
    ├── styles.css    # Enhanced dark theme
    └── app.js        # Chart.js charts, tabs, live feed, catalog

examples/
└── demo.py           # Colorful demo simulation (10+ providers)
```

---

## 🧪 Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## 📝 License

MIT

