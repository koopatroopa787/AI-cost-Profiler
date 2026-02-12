"""Pricing engine for LLM cost calculation."""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from .models import Provider


@dataclass
class ModelPricing:
    """Pricing per 1M tokens for a model."""
    input_price: float  # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Tuple[float, float]:
        """Calculate cost for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price
        return input_cost, output_cost


# Current pricing as of Feb 2026 (update periodically)
DEFAULT_PRICING: Dict[str, ModelPricing] = {
    # OpenAI Models
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "gpt-4-turbo": ModelPricing(10.00, 30.00),
    "gpt-4": ModelPricing(30.00, 60.00),
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50),
    "o1": ModelPricing(15.00, 60.00),
    "o1-mini": ModelPricing(3.00, 12.00),
    "o3-mini": ModelPricing(1.10, 4.40),
    
    # Anthropic Models
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00),
    "claude-3-opus-20240229": ModelPricing(15.00, 75.00),
    "claude-3-sonnet-20240229": ModelPricing(3.00, 15.00),
    "claude-3-haiku-20240307": ModelPricing(0.25, 1.25),
    
    # Shorthand aliases
    "claude-3-5-sonnet": ModelPricing(3.00, 15.00),
    "claude-3-5-haiku": ModelPricing(0.80, 4.00),
    "claude-3-opus": ModelPricing(15.00, 75.00),
    "claude-3-sonnet": ModelPricing(3.00, 15.00),
    "claude-3-haiku": ModelPricing(0.25, 1.25),
    
    # Google Models
    "gemini-2.0-flash": ModelPricing(0.10, 0.40),
    "gemini-1.5-pro": ModelPricing(1.25, 5.00),
    "gemini-1.5-flash": ModelPricing(0.075, 0.30),
    
    # Mistral Models
    "mistral-large": ModelPricing(2.00, 6.00),
    "mistral-medium": ModelPricing(2.70, 8.10),
    "mistral-small": ModelPricing(0.20, 0.60),
    "codestral": ModelPricing(0.20, 0.60),
    
    # Cohere Models
    "command-r-plus": ModelPricing(2.50, 10.00),
    "command-r": ModelPricing(0.15, 0.60),
}


class PricingEngine:
    """Engine for calculating LLM costs."""
    
    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        self.pricing = DEFAULT_PRICING.copy()
        if custom_pricing:
            self.pricing.update(custom_pricing)
    
    def get_model_pricing(self, model: str) -> Optional[ModelPricing]:
        """Get pricing for a model, with fuzzy matching."""
        # Exact match
        if model in self.pricing:
            return self.pricing[model]
        
        # Try prefix matching (e.g., "gpt-4o-2024-08-06" -> "gpt-4o")
        for known_model in self.pricing:
            if model.startswith(known_model):
                return self.pricing[known_model]
        
        # Try suffix matching for versioned models
        model_base = model.rsplit("-", 1)[0] if "-" in model else model
        if model_base in self.pricing:
            return self.pricing[model_base]
        
        return None
    
    def calculate_cost(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int,
        provider: Provider = Provider.OPENAI
    ) -> Tuple[float, float, float]:
        """
        Calculate cost for a request.
        
        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        pricing = self.get_model_pricing(model)
        
        if pricing is None:
            # Use conservative default pricing if model unknown
            pricing = ModelPricing(10.00, 30.00)  # Assume expensive
        
        input_cost, output_cost = pricing.calculate_cost(input_tokens, output_tokens)
        return input_cost, output_cost, input_cost + output_cost
    
    def add_custom_pricing(self, model: str, input_price: float, output_price: float):
        """Add or update pricing for a model."""
        self.pricing[model] = ModelPricing(input_price, output_price)
    
    def get_cheaper_alternatives(self, model: str, provider: Optional[Provider] = None) -> list:
        """Get list of cheaper models that could be alternatives."""
        current_pricing = self.get_model_pricing(model)
        if not current_pricing:
            return []
        
        alternatives = []
        current_avg = (current_pricing.input_price + current_pricing.output_price) / 2
        
        for name, pricing in self.pricing.items():
            if name == model:
                continue
            alt_avg = (pricing.input_price + pricing.output_price) / 2
            if alt_avg < current_avg:
                savings_pct = ((current_avg - alt_avg) / current_avg) * 100
                alternatives.append({
                    "model": name,
                    "input_price": pricing.input_price,
                    "output_price": pricing.output_price,
                    "savings_percent": round(savings_pct, 1)
                })
        
        # Sort by savings
        alternatives.sort(key=lambda x: x["savings_percent"], reverse=True)
        return alternatives[:5]  # Top 5 alternatives
