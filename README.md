# AI Cost Profiler

**Lightweight SDK to instrument AI agent applications and track LLM costs in real-time.**

> "Your customer support agent just spent $47 in 10 minutes"

## ✨ Features

- 📊 **Real-time cost tracking** per agent, task, and user
- 💰 **Accurate pricing** for OpenAI, Anthropic, Google, Mistral, Cohere
- 🔍 **Expensive prompt identification** - find prompts using 3x more tokens
- 💡 **Optimization suggestions** - "Switch to Claude Haiku here, save $2K/month"
- 🖥️ **Live dashboard** with WebSocket updates
- 🪶 **Lightweight** - minimal overhead on your application

## 📦 Installation

```bash
pip install -e .
```

## 🚀 Quick Start

### Basic Usage

```python
from ai_cost_profiler import CostTracker

tracker = CostTracker()

# Using decorator
@tracker.track(agent="customer_support", task="answer_question")
def my_agent_function():
    response = openai.chat.completions.create(...)
    return response

# Using context manager
with tracker.track_context(agent="customer_support", task="answer_question") as ctx:
    response = openai.chat.completions.create(...)
    ctx.record_response(response)

# Manual recording
tracker.record(
    agent="customer_support",
    task="answer_question",
    model="gpt-4o",
    input_tokens=100,
    output_tokens=50
)
```

### With OpenAI

```python
from openai import OpenAI
from ai_cost_profiler import CostTracker

client = OpenAI()
tracker = CostTracker()

@tracker.track(agent="support_bot", task="chat")
def chat(message: str):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message}]
    )

response = chat("Hello, how can I track my order?")
# Cost automatically recorded!
```

### With Anthropic

```python
from anthropic import Anthropic
from ai_cost_profiler import CostTracker, Provider

client = Anthropic()
tracker = CostTracker()

@tracker.track(agent="analyst", task="summarize", provider=Provider.ANTHROPIC)
def summarize(doc: str):
    return client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": f"Summarize: {doc}"}]
    )
```

## 📊 Dashboard

Start the real-time cost monitoring dashboard:

```bash
# Start the dashboard
cd e:\claude_code_app
python -m uvicorn dashboard.app:app --reload

# Open http://127.0.0.1:8000
```

Run the demo to generate sample data:

```bash
python examples/demo.py
```

## 🔌 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/costs/summary` | Overall cost summary |
| `GET /api/costs/by-agent` | Cost breakdown by agent |
| `GET /api/costs/by-task` | Cost breakdown by task |
| `GET /api/costs/expensive-prompts` | Top expensive prompts |
| `GET /api/suggestions` | Optimization recommendations |
| `WS /ws/live` | Real-time WebSocket updates |

## 💰 Supported Models

### OpenAI
- GPT-4o, GPT-4o-mini
- GPT-4-turbo, GPT-4
- GPT-3.5-turbo
- o1, o1-mini, o3-mini

### Anthropic
- Claude 3.5 Sonnet, Claude 3.5 Haiku
- Claude 3 Opus, Sonnet, Haiku

### Google
- Gemini 2.0 Flash
- Gemini 1.5 Pro, Flash

### Mistral
- Mistral Large, Medium, Small
- Codestral

### Cohere
- Command R+, Command R

## 📁 Project Structure

```
ai_cost_profiler/
├── __init__.py      # Package exports
├── tracker.py       # Main CostTracker class
├── models.py        # Data models
├── pricing.py       # Cost calculation
├── token_counter.py # Token counting
├── storage.py       # SQLite storage
└── analytics.py     # Analytics & suggestions

dashboard/
├── __init__.py
├── app.py           # FastAPI server
└── static/
    ├── index.html   # Dashboard UI
    ├── styles.css   # Nothing OS design
    └── app.js       # WebSocket client

examples/
└── demo.py          # Demo script
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v
```

## 📝 License

MIT
