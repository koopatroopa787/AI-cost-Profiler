"""Data models for AI Cost Profiler."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Provider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    GROQ = "groq"
    TOGETHER = "together"
    PERPLEXITY = "perplexity"
    AI21 = "ai21"
    META = "meta"
    AMAZON = "amazon"
    AZURE = "azure"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    FIREWORKS = "fireworks"
    OPENROUTER = "openrouter"
    REPLICATE = "replicate"
    ANYSCALE = "anyscale"
    CUSTOM = "custom"


@dataclass
class UsageRecord:
    """Single usage record for an LLM call."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Attribution
    agent: str = "default"
    task: str = "default"
    user: Optional[str] = None
    
    # Provider info
    provider: Provider = Provider.OPENAI
    model: str = "gpt-4"
    
    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # Cost in USD
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    
    # Prompt info for analysis
    prompt_hash: Optional[str] = None
    prompt_preview: Optional[str] = None  # First 200 chars
    
    # Response time in ms
    latency_ms: Optional[int] = None
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
        if self.total_cost == 0:
            self.total_cost = self.input_cost + self.output_cost


@dataclass
class CostSummary:
    """Aggregated cost summary."""
    total_cost: float = 0.0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    request_count: int = 0
    avg_cost_per_request: float = 0.0
    avg_tokens_per_request: float = 0.0
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


@dataclass
class AgentCost:
    """Cost breakdown for a specific agent."""
    agent: str
    total_cost: float = 0.0
    total_tokens: int = 0
    request_count: int = 0
    avg_cost_per_request: float = 0.0
    top_model: Optional[str] = None
    top_task: Optional[str] = None


@dataclass
class TaskCost:
    """Cost breakdown for a specific task."""
    task: str
    agent: str
    total_cost: float = 0.0
    total_tokens: int = 0
    request_count: int = 0
    avg_cost_per_request: float = 0.0


@dataclass
class UserCost:
    """Cost breakdown for a specific user."""
    user: str
    total_cost: float = 0.0
    total_tokens: int = 0
    request_count: int = 0
    agents_used: list = field(default_factory=list)


@dataclass 
class ExpensivePrompt:
    """Information about an expensive prompt."""
    prompt_hash: str
    prompt_preview: str
    avg_tokens: float
    avg_cost: float
    call_count: int
    total_cost: float
    agent: str
    task: str
    model: str
    # Comparison to similar prompts
    token_ratio_vs_avg: float = 1.0  # e.g., 3.0 means 3x more tokens than average


@dataclass
class BudgetRule:
    limit: float
    period: str
    agent: Optional[str] = None
    user: Optional[str] = None