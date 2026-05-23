"""Configuration management for cloii-cli"""
import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "cloii-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "ollama_host": "http://localhost:11434",
    "debug": False,
    "max_tokens": 4096,
    "system_prompt": (
        "You are cloii-cli, a personal AI coding agent. "
        "You can read/write files, run shell commands, search the web, and help with code. "
        "Be concise, helpful, and proactive. When coding, always write complete working solutions."
    ),
}

FREE_PROVIDERS = {
    "ollama": {
        "name": "Ollama (Local)",
        "description": "Local models, fully offline, no API key needed",
        "models": ["qwen2.5-coder:7b", "qwen3:8b", "llama3.2:3b", "gemma3:4b", "phi4-mini"],
    },
    "groq": {
        "name": "Groq (Free Tier)",
        "description": "Very fast inference, generous free tier",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"],
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "openrouter": {
        "name": "OpenRouter (Free models)",
        "description": "Free models from many providers",
        "models": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen3-8b:free",
        ],
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception:
                pass
        # Environment overrides
        for key, env in [
            ("provider", "CLOII_PROVIDER"),
            ("model", "CLOII_MODEL"),
            ("ollama_host", "CLOII_OLLAMA_HOST"),
        ]:
            val = os.environ.get(env)
            if val:
                self._data[key] = val

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        return self._data.get(key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def get_provider_info(self):
        return FREE_PROVIDERS.get(self.provider, {})

    def get_api_key(self):
        info = self.get_provider_info()
        env = info.get("api_key_env")
        if env:
            return os.environ.get(env)
        return None
