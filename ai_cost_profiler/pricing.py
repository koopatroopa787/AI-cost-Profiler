"""Pricing engine for LLM cost calculation."""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from .models import Provider


@dataclass
class ModelPricing:
    """Pricing per 1M tokens for a model."""
    input_price: float   # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    provider: str = "custom"
    context_window: int = 0      # Max context in tokens (0 = unknown)
    supports_vision: bool = False
    supports_tools: bool = False
    description: str = ""

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Tuple[float, float]:
        """Calculate cost for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price
        return input_cost, output_cost


# Current pricing as of April 2026 (USD per 1M tokens)
# Sources: official provider pricing pages
DEFAULT_PRICING: Dict[str, ModelPricing] = {

    # ── OpenAI ──────────────────────────────────────────────────────────────
    "gpt-4o": ModelPricing(2.50, 10.00, "openai", 128_000, True, True,
                           "OpenAI GPT-4o – multimodal flagship"),
    "gpt-4o-mini": ModelPricing(0.15, 0.60, "openai", 128_000, True, True,
                                "OpenAI GPT-4o Mini – fast & affordable"),
    "gpt-4-turbo": ModelPricing(10.00, 30.00, "openai", 128_000, True, True,
                                "OpenAI GPT-4 Turbo"),
    "gpt-4": ModelPricing(30.00, 60.00, "openai", 8_192, False, True,
                          "OpenAI GPT-4 original"),
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50, "openai", 16_385, False, True,
                                  "OpenAI GPT-3.5 Turbo – legacy fast model"),
    "o1": ModelPricing(15.00, 60.00, "openai", 200_000, True, True,
                       "OpenAI o1 reasoning model"),
    "o1-mini": ModelPricing(3.00, 12.00, "openai", 128_000, False, False,
                            "OpenAI o1-mini – compact reasoning"),
    "o1-preview": ModelPricing(15.00, 60.00, "openai", 128_000, False, False,
                               "OpenAI o1 preview"),
    "o3": ModelPricing(10.00, 40.00, "openai", 200_000, True, True,
                       "OpenAI o3 advanced reasoning"),
    "o3-mini": ModelPricing(1.10, 4.40, "openai", 200_000, False, True,
                            "OpenAI o3-mini reasoning"),
    "o4-mini": ModelPricing(1.10, 4.40, "openai", 200_000, True, True,
                            "OpenAI o4-mini"),
    "gpt-4.1": ModelPricing(2.00, 8.00, "openai", 1_000_000, True, True,
                            "OpenAI GPT-4.1 – 1M context"),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60, "openai", 1_000_000, True, True,
                                 "OpenAI GPT-4.1 Mini"),
    "gpt-4.1-nano": ModelPricing(0.10, 0.40, "openai", 1_000_000, True, True,
                                 "OpenAI GPT-4.1 Nano – cheapest GPT-4 class"),

    # ── Anthropic ───────────────────────────────────────────────────────────
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00, "anthropic", 200_000, True, True,
                                               "Claude 3.5 Sonnet (Oct 2024)"),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00, "anthropic", 200_000, True, True,
                                              "Claude 3.5 Haiku (Oct 2024)"),
    "claude-3-opus-20240229": ModelPricing(15.00, 75.00, "anthropic", 200_000, True, True,
                                           "Claude 3 Opus"),
    "claude-3-sonnet-20240229": ModelPricing(3.00, 15.00, "anthropic", 200_000, True, True,
                                             "Claude 3 Sonnet"),
    "claude-3-haiku-20240307": ModelPricing(0.25, 1.25, "anthropic", 200_000, True, True,
                                            "Claude 3 Haiku"),
    "claude-opus-4": ModelPricing(15.00, 75.00, "anthropic", 200_000, True, True,
                                  "Claude Opus 4"),
    "claude-sonnet-4": ModelPricing(3.00, 15.00, "anthropic", 200_000, True, True,
                                    "Claude Sonnet 4"),
    "claude-haiku-4": ModelPricing(0.80, 4.00, "anthropic", 200_000, True, True,
                                   "Claude Haiku 4"),
    # Shorthand aliases
    "claude-3-5-sonnet": ModelPricing(3.00, 15.00, "anthropic", 200_000, True, True,
                                      "Claude 3.5 Sonnet"),
    "claude-3-5-haiku": ModelPricing(0.80, 4.00, "anthropic", 200_000, True, True,
                                     "Claude 3.5 Haiku"),
    "claude-3-opus": ModelPricing(15.00, 75.00, "anthropic", 200_000, True, True,
                                  "Claude 3 Opus"),
    "claude-3-sonnet": ModelPricing(3.00, 15.00, "anthropic", 200_000, True, True,
                                    "Claude 3 Sonnet"),
    "claude-3-haiku": ModelPricing(0.25, 1.25, "anthropic", 200_000, True, True,
                                   "Claude 3 Haiku"),

    # ── Google Gemini ────────────────────────────────────────────────────────
    "gemini-2.5-pro": ModelPricing(1.25, 10.00, "google", 1_000_000, True, True,
                                   "Gemini 2.5 Pro – 1M context"),
    "gemini-2.5-flash": ModelPricing(0.075, 0.30, "google", 1_000_000, True, True,
                                     "Gemini 2.5 Flash – ultra-fast"),
    "gemini-2.0-flash": ModelPricing(0.10, 0.40, "google", 1_000_000, True, True,
                                     "Gemini 2.0 Flash"),
    "gemini-2.0-flash-lite": ModelPricing(0.075, 0.30, "google", 1_000_000, True, False,
                                          "Gemini 2.0 Flash Lite"),
    "gemini-1.5-pro": ModelPricing(1.25, 5.00, "google", 2_000_000, True, True,
                                   "Gemini 1.5 Pro – 2M context"),
    "gemini-1.5-flash": ModelPricing(0.075, 0.30, "google", 1_000_000, True, True,
                                     "Gemini 1.5 Flash"),
    "gemini-1.5-flash-8b": ModelPricing(0.0375, 0.15, "google", 1_000_000, True, False,
                                        "Gemini 1.5 Flash 8B"),
    "gemini-1.0-pro": ModelPricing(0.50, 1.50, "google", 32_760, False, False,
                                   "Gemini 1.0 Pro – legacy"),

    # ── Mistral AI ───────────────────────────────────────────────────────────
    "mistral-large-2": ModelPricing(2.00, 6.00, "mistral", 128_000, False, True,
                                    "Mistral Large 2 – flagship"),
    "mistral-large": ModelPricing(2.00, 6.00, "mistral", 32_000, False, True,
                                  "Mistral Large"),
    "mistral-medium": ModelPricing(2.70, 8.10, "mistral", 32_000, False, False,
                                   "Mistral Medium – legacy"),
    "mistral-small": ModelPricing(0.20, 0.60, "mistral", 32_000, False, True,
                                  "Mistral Small"),
    "mistral-nemo": ModelPricing(0.15, 0.15, "mistral", 128_000, False, True,
                                 "Mistral NeMo 12B – open, via API"),
    "codestral": ModelPricing(0.20, 0.60, "mistral", 32_000, False, False,
                              "Codestral – code specialist"),
    "codestral-mamba": ModelPricing(0.20, 0.60, "mistral", 256_000, False, False,
                                    "Codestral Mamba – unlimited context"),
    "mixtral-8x22b-instruct": ModelPricing(1.20, 1.20, "mistral", 65_536, False, False,
                                           "Mixtral 8×22B Instruct"),
    "mixtral-8x7b-instruct": ModelPricing(0.70, 0.70, "mistral", 32_768, False, False,
                                          "Mixtral 8×7B Instruct"),
    "mistral-7b-instruct": ModelPricing(0.25, 0.25, "mistral", 32_768, False, False,
                                        "Mistral 7B Instruct"),

    # ── DeepSeek ─────────────────────────────────────────────────────────────
    "deepseek-chat": ModelPricing(0.27, 1.10, "deepseek", 64_000, False, True,
                                  "DeepSeek-V3 Chat – ultra-affordable"),
    "deepseek-reasoner": ModelPricing(0.55, 2.19, "deepseek", 64_000, False, False,
                                      "DeepSeek-R1 Reasoner"),
    "deepseek-coder": ModelPricing(0.14, 0.28, "deepseek", 128_000, False, False,
                                   "DeepSeek Coder – code generation"),
    "deepseek-v3": ModelPricing(0.27, 1.10, "deepseek", 64_000, False, True,
                                "DeepSeek V3"),
    "deepseek-r1": ModelPricing(0.55, 2.19, "deepseek", 64_000, False, False,
                                "DeepSeek R1"),

    # ── xAI (Grok) ───────────────────────────────────────────────────────────
    "grok-3": ModelPricing(3.00, 15.00, "xai", 131_072, True, True,
                           "xAI Grok 3 – flagship"),
    "grok-3-mini": ModelPricing(0.30, 0.50, "xai", 131_072, False, True,
                                "xAI Grok 3 Mini – fast reasoning"),
    "grok-2": ModelPricing(2.00, 10.00, "xai", 131_072, True, True,
                           "xAI Grok 2"),
    "grok-2-mini": ModelPricing(0.20, 1.00, "xai", 131_072, False, False,
                                "xAI Grok 2 Mini"),
    "grok-beta": ModelPricing(5.00, 15.00, "xai", 131_072, True, False,
                              "xAI Grok Beta"),

    # ── Cohere ───────────────────────────────────────────────────────────────
    "command-r-plus": ModelPricing(2.50, 10.00, "cohere", 128_000, False, True,
                                   "Cohere Command R+ – RAG-optimised"),
    "command-r": ModelPricing(0.15, 0.60, "cohere", 128_000, False, True,
                              "Cohere Command R"),
    "command-r-08-2024": ModelPricing(0.15, 0.60, "cohere", 128_000, False, True,
                                      "Cohere Command R (Aug 2024)"),
    "command-light": ModelPricing(0.30, 0.60, "cohere", 4_096, False, False,
                                  "Cohere Command Light"),
    "command-nightly": ModelPricing(1.00, 2.00, "cohere", 4_096, False, False,
                                    "Cohere Command Nightly"),

    # ── AI21 Labs ────────────────────────────────────────────────────────────
    "jamba-1.5-large": ModelPricing(2.00, 8.00, "ai21", 256_000, False, True,
                                    "AI21 Jamba 1.5 Large – 256K context"),
    "jamba-1.5-mini": ModelPricing(0.20, 0.40, "ai21", 256_000, False, True,
                                   "AI21 Jamba 1.5 Mini"),
    "jamba-instruct": ModelPricing(0.50, 0.70, "ai21", 256_000, False, False,
                                   "AI21 Jamba Instruct"),

    # ── Groq (fast inference) ────────────────────────────────────────────────
    "llama-3.3-70b-versatile": ModelPricing(0.59, 0.79, "groq", 128_000, False, True,
                                            "Llama 3.3 70B via Groq"),
    "llama-3.1-8b-instant": ModelPricing(0.05, 0.08, "groq", 128_000, False, True,
                                         "Llama 3.1 8B Instant via Groq"),
    "mixtral-8x7b-32768": ModelPricing(0.24, 0.24, "groq", 32_768, False, False,
                                       "Mixtral 8×7B via Groq"),
    "gemma2-9b-it": ModelPricing(0.20, 0.20, "groq", 8_192, False, False,
                                 "Gemma 2 9B IT via Groq"),

    # ── Together AI ──────────────────────────────────────────────────────────
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": ModelPricing(0.88, 0.88, "together", 131_072, False, True,
                                                              "Llama 3.3 70B Turbo via Together"),
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": ModelPricing(0.18, 0.18, "together", 128_000, False, True,
                                                                  "Llama 3.1 8B Turbo via Together"),
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": ModelPricing(0.88, 0.88, "together", 128_000, False, True,
                                                                   "Llama 3.1 70B Turbo via Together"),
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": ModelPricing(5.00, 5.00, "together", 128_000, False, True,
                                                                    "Llama 3.1 405B Turbo via Together"),
    "Qwen/Qwen2.5-72B-Instruct-Turbo": ModelPricing(1.20, 1.20, "together", 32_768, False, True,
                                                      "Qwen 2.5 72B via Together"),
    "mistralai/Mixtral-8x7B-Instruct-v0.1": ModelPricing(0.60, 0.60, "together", 32_768, False, False,
                                                           "Mixtral 8×7B via Together"),
    "deepseek-ai/DeepSeek-R1": ModelPricing(3.00, 7.00, "together", 64_000, False, False,
                                             "DeepSeek R1 via Together"),

    # ── Perplexity ───────────────────────────────────────────────────────────
    "llama-3.1-sonar-small-128k-online": ModelPricing(0.20, 0.20, "perplexity", 127_072, False, False,
                                                       "Perplexity Sonar Small Online"),
    "llama-3.1-sonar-large-128k-online": ModelPricing(1.00, 1.00, "perplexity", 127_072, False, False,
                                                       "Perplexity Sonar Large Online"),
    "llama-3.1-sonar-huge-128k-online": ModelPricing(5.00, 5.00, "perplexity", 127_072, False, False,
                                                      "Perplexity Sonar Huge Online"),
    "sonar-pro": ModelPricing(3.00, 15.00, "perplexity", 200_000, False, False,
                              "Perplexity Sonar Pro"),
    "sonar": ModelPricing(1.00, 1.00, "perplexity", 127_072, False, False,
                          "Perplexity Sonar"),

    # ── Meta Llama (self-hosted reference pricing) ───────────────────────────
    "llama-3.2-1b-instruct": ModelPricing(0.04, 0.04, "meta", 128_000, False, False,
                                          "Llama 3.2 1B Instruct – tiny"),
    "llama-3.2-3b-instruct": ModelPricing(0.06, 0.06, "meta", 128_000, False, False,
                                          "Llama 3.2 3B Instruct"),
    "llama-3.2-11b-instruct": ModelPricing(0.18, 0.18, "meta", 128_000, True, False,
                                           "Llama 3.2 11B Vision"),
    "llama-3.2-90b-instruct": ModelPricing(0.90, 0.90, "meta", 128_000, True, False,
                                           "Llama 3.2 90B Vision"),
    "llama-3.1-8b-instruct": ModelPricing(0.18, 0.18, "meta", 128_000, False, True,
                                          "Llama 3.1 8B Instruct"),
    "llama-3.1-70b-instruct": ModelPricing(0.88, 0.88, "meta", 128_000, False, True,
                                           "Llama 3.1 70B Instruct"),
    "llama-3.1-405b-instruct": ModelPricing(5.00, 5.00, "meta", 128_000, False, True,
                                            "Llama 3.1 405B Instruct"),
    "llama-3-8b-instruct": ModelPricing(0.20, 0.20, "meta", 8_000, False, False,
                                        "Llama 3 8B Instruct"),
    "llama-3-70b-instruct": ModelPricing(0.90, 0.90, "meta", 8_000, False, False,
                                         "Llama 3 70B Instruct"),

    # ── Fireworks AI ─────────────────────────────────────────────────────────
    "accounts/fireworks/models/llama-v3p1-8b-instruct": ModelPricing(0.20, 0.20, "fireworks", 131_072, False, False,
                                                                      "Llama 3.1 8B via Fireworks"),
    "accounts/fireworks/models/llama-v3p1-70b-instruct": ModelPricing(0.90, 0.90, "fireworks", 131_072, False, False,
                                                                       "Llama 3.1 70B via Fireworks"),
    "accounts/fireworks/models/firefunction-v2": ModelPricing(0.90, 0.90, "fireworks", 8_192, False, True,
                                                               "Fireworks FireFunction v2 – tool use"),

    # ── Amazon Bedrock ───────────────────────────────────────────────────────
    "amazon.titan-text-express-v1": ModelPricing(0.20, 0.60, "amazon", 8_000, False, False,
                                                 "Amazon Titan Text Express"),
    "amazon.titan-text-lite-v1": ModelPricing(0.30, 0.40, "amazon", 4_000, False, False,
                                              "Amazon Titan Text Lite"),
    "amazon.nova-pro-v1": ModelPricing(0.80, 3.20, "amazon", 300_000, True, True,
                                       "Amazon Nova Pro"),
    "amazon.nova-lite-v1": ModelPricing(0.06, 0.24, "amazon", 300_000, True, True,
                                        "Amazon Nova Lite"),
    "amazon.nova-micro-v1": ModelPricing(0.035, 0.14, "amazon", 128_000, False, False,
                                         "Amazon Nova Micro – cheapest Bedrock"),

    # ── Ollama / Local Models (free) ─────────────────────────────────────────
    "ollama/llama3.2": ModelPricing(0.0, 0.0, "ollama", 128_000, False, False,
                                    "Llama 3.2 via Ollama – FREE local"),
    "ollama/llama3.1": ModelPricing(0.0, 0.0, "ollama", 128_000, False, False,
                                    "Llama 3.1 via Ollama – FREE local"),
    "ollama/mistral": ModelPricing(0.0, 0.0, "ollama", 32_768, False, False,
                                   "Mistral via Ollama – FREE local"),
    "ollama/gemma2": ModelPricing(0.0, 0.0, "ollama", 8_192, False, False,
                                  "Gemma 2 via Ollama – FREE local"),
    "ollama/qwen2.5": ModelPricing(0.0, 0.0, "ollama", 32_768, False, False,
                                   "Qwen 2.5 via Ollama – FREE local"),
    "ollama/deepseek-r1": ModelPricing(0.0, 0.0, "ollama", 64_000, False, False,
                                       "DeepSeek R1 via Ollama – FREE local"),
    "ollama/phi4": ModelPricing(0.0, 0.0, "ollama", 16_000, False, False,
                                "Microsoft Phi-4 via Ollama – FREE local"),
    "local": ModelPricing(0.0, 0.0, "ollama", 0, False, False,
                          "Any local / self-hosted model – FREE"),
}

# Provider-level metadata (display name, website, icon character)
PROVIDER_INFO: Dict[str, Dict[str, str]] = {
    "openai":      {"name": "OpenAI",       "url": "https://openai.com",         "icon": "🟢"},
    "anthropic":   {"name": "Anthropic",    "url": "https://anthropic.com",      "icon": "🟠"},
    "google":      {"name": "Google",       "url": "https://ai.google.dev",      "icon": "🔵"},
    "mistral":     {"name": "Mistral AI",   "url": "https://mistral.ai",         "icon": "🟣"},
    "deepseek":    {"name": "DeepSeek",     "url": "https://deepseek.com",       "icon": "🔷"},
    "xai":         {"name": "xAI (Grok)",   "url": "https://x.ai",               "icon": "⚫"},
    "cohere":      {"name": "Cohere",       "url": "https://cohere.com",         "icon": "🔴"},
    "ai21":        {"name": "AI21 Labs",    "url": "https://ai21.com",           "icon": "🟡"},
    "groq":        {"name": "Groq",         "url": "https://groq.com",           "icon": "⚡"},
    "together":    {"name": "Together AI",  "url": "https://together.ai",        "icon": "🤝"},
    "perplexity":  {"name": "Perplexity",   "url": "https://perplexity.ai",      "icon": "🔍"},
    "meta":        {"name": "Meta (Llama)", "url": "https://llama.meta.com",     "icon": "🦙"},
    "amazon":      {"name": "AWS Bedrock",  "url": "https://aws.amazon.com/bedrock", "icon": "☁️"},
    "fireworks":   {"name": "Fireworks AI", "url": "https://fireworks.ai",       "icon": "🎆"},
    "ollama":      {"name": "Ollama/Local", "url": "https://ollama.ai",          "icon": "🏠"},
    "openrouter":  {"name": "OpenRouter",   "url": "https://openrouter.ai",      "icon": "🔀"},
    "replicate":   {"name": "Replicate",    "url": "https://replicate.com",      "icon": "♻️"},
    "azure":       {"name": "Azure OpenAI", "url": "https://azure.microsoft.com","icon": "🌐"},
    "huggingface": {"name": "HuggingFace",  "url": "https://huggingface.co",     "icon": "🤗"},
    "custom":      {"name": "Custom",       "url": "",                           "icon": "⚙️"},
}


class PricingEngine:
    """Engine for calculating LLM costs."""

    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        self.pricing = DEFAULT_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)

    def get_model_pricing(self, model: str) -> Optional[ModelPricing]:
        """Get pricing for a model, with fuzzy matching."""
        if not model:
            return None
        model_lower = model.lower()

        # Exact match (case-insensitive)
        for key, val in self.pricing.items():
            if key.lower() == model_lower:
                return val

        # Prefix matching (e.g., "gpt-4o-2024-08-06" -> "gpt-4o")
        for key, val in self.pricing.items():
            if model_lower.startswith(key.lower()):
                return val

        # Suffix / partial matching for versioned models
        model_base = model_lower.rsplit("-", 1)[0] if "-" in model_lower else model_lower
        for key, val in self.pricing.items():
            if key.lower() == model_base:
                return val

        # Fuzzy: check if any known key is a substring of the model name
        for key, val in self.pricing.items():
            if key.lower() in model_lower:
                return val

        return None

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Provider = Provider.OPENAI,
    ) -> Tuple[float, float, float]:
        """
        Calculate cost for a request.

        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        pricing = self.get_model_pricing(model)

        if pricing is None:
            # Conservative default if model unknown
            pricing = ModelPricing(10.00, 30.00)

        input_cost, output_cost = pricing.calculate_cost(input_tokens, output_tokens)
        return input_cost, output_cost, input_cost + output_cost

    def add_custom_pricing(self, model: str, input_price: float, output_price: float,
                           provider: str = "custom", description: str = "") -> None:
        """Add or update pricing for a model."""
        self.pricing[model] = ModelPricing(input_price, output_price, provider,
                                           description=description)

    def get_cheaper_alternatives(self, model: str, provider: Optional[Provider] = None,
                                 top_n: int = 5) -> List[dict]:
        """Get list of cheaper models that could be alternatives."""
        current_pricing = self.get_model_pricing(model)
        if not current_pricing:
            return []

        current_avg = (current_pricing.input_price + current_pricing.output_price) / 2

        alternatives = []
        seen: set = set()
        for name, pricing in self.pricing.items():
            if name == model or name in seen:
                continue
            seen.add(name)
            alt_avg = (pricing.input_price + pricing.output_price) / 2
            if alt_avg < current_avg:
                savings_pct = ((current_avg - alt_avg) / current_avg) * 100
                alternatives.append({
                    "model": name,
                    "provider": pricing.provider,
                    "input_price": pricing.input_price,
                    "output_price": pricing.output_price,
                    "savings_percent": round(savings_pct, 1),
                    "description": pricing.description,
                })

        alternatives.sort(key=lambda x: x["savings_percent"], reverse=True)
        return alternatives[:top_n]

    def list_models(self, provider: Optional[str] = None) -> List[dict]:
        """Return list of all known models with their pricing."""
        seen: set = set()
        result = []
        for name, p in self.pricing.items():
            if name in seen:
                continue
            seen.add(name)
            if provider and p.provider != provider:
                continue
            result.append({
                "model": name,
                "provider": p.provider,
                "input_per_1m": p.input_price,
                "output_per_1m": p.output_price,
                "context_window": p.context_window,
                "supports_vision": p.supports_vision,
                "supports_tools": p.supports_tools,
                "description": p.description,
            })
        result.sort(key=lambda x: (x["provider"], x["input_per_1m"]))
        return result

    def get_provider_summary(self) -> List[dict]:
        """Return one entry per provider with model count and cheapest model."""
        providers: Dict[str, dict] = {}
        for name, p in self.pricing.items():
            if p.provider not in providers:
                providers[p.provider] = {
                    "provider": p.provider,
                    "model_count": 0,
                    "cheapest_input": float("inf"),
                    "cheapest_model": name,
                }
            providers[p.provider]["model_count"] += 1
            if p.input_price < providers[p.provider]["cheapest_input"]:
                providers[p.provider]["cheapest_input"] = p.input_price
                providers[p.provider]["cheapest_model"] = name
        return sorted(providers.values(), key=lambda x: x["provider"])
