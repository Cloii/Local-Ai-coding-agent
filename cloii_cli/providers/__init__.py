from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider


def get_provider(config):
    if config.provider == "ollama":
        return OllamaProvider(config)
    elif config.provider in ("groq", "openrouter"):
        return OpenAICompatProvider(config)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")
