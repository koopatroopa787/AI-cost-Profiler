"""Token counting utilities using tiktoken."""

import hashlib
from typing import Optional, List, Dict, Any

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TokenCounter:
    """Count tokens for various models."""
    
    # Model to encoding mapping
    MODEL_ENCODINGS = {
        # OpenAI models use cl100k_base or o200k_base
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "o1": "o200k_base",
        "o1-mini": "o200k_base",
        "o3-mini": "o200k_base",
        
        # Anthropic models (approximate with cl100k_base)
        "claude-3": "cl100k_base",
        "claude-3-5": "cl100k_base",
    }
    
    def __init__(self):
        self._encoders: Dict[str, Any] = {}
    
    def _get_encoder(self, model: str) -> Any:
        """Get tiktoken encoder for a model."""
        if not TIKTOKEN_AVAILABLE:
            return None
        
        # Find encoding for model
        encoding_name = "cl100k_base"  # Default
        for model_prefix, enc_name in self.MODEL_ENCODINGS.items():
            if model.startswith(model_prefix):
                encoding_name = enc_name
                break
        
        if encoding_name not in self._encoders:
            try:
                self._encoders[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception:
                self._encoders[encoding_name] = tiktoken.get_encoding("cl100k_base")
        
        return self._encoders[encoding_name]
    
    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """Count tokens in a text string."""
        if not text:
            return 0
        
        encoder = self._get_encoder(model)
        if encoder is None:
            # Fallback: approximate 1 token = 4 characters
            return len(text) // 4
        
        return len(encoder.encode(text))
    
    def count_message_tokens(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o"
    ) -> int:
        """Count tokens in a list of chat messages."""
        if not messages:
            return 0
        
        encoder = self._get_encoder(model)
        if encoder is None:
            # Fallback
            total_chars = sum(len(m.get("content", "")) for m in messages)
            return total_chars // 4
        
        # Token overhead per message varies by model
        tokens_per_message = 4  # Approximate overhead
        
        total = 0
        for message in messages:
            total += tokens_per_message
            for key, value in message.items():
                if isinstance(value, str):
                    total += len(encoder.encode(value))
        
        total += 3  # Reply priming tokens
        return total
    
    def hash_prompt(self, text: str) -> str:
        """Create a hash of a prompt for deduplication."""
        # Normalize whitespace
        normalized = " ".join(text.split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get_prompt_preview(self, text: str, max_length: int = 200) -> str:
        """Get a preview of a prompt for display."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."


# Singleton instance
_token_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get the global token counter instance."""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
