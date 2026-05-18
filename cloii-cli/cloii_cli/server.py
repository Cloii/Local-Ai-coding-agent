"""JSON-line server mode — communicates with Electron desktop via stdin/stdout"""
import sys
import json
import threading
from .providers import get_provider
from .agent import Agent
from .config import FREE_PROVIDERS


class Server:
    def __init__(self, config):
        self.config = config
        self.provider = None
        self.agent = None
        self._init_provider()

    def _init_provider(self):
        try:
            self.provider = get_provider(self.config)
            self.agent = Agent(self.config, self.provider)
        except Exception as e:
            self._send({"type": "error", "message": str(e)})

    def _send(self, obj):
        line = json.dumps(obj, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def run(self):
        self._send({"type": "ready", "provider": self.config.provider, "model": self.config.model})
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                self._handle(msg)
            except json.JSONDecodeError:
                self._send({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                self._send({"type": "error", "message": str(e)})

    def _handle(self, msg):
        kind = msg.get("type")

        if kind == "chat":
            text = msg.get("text", "")
            self.agent.add_user(text)
            try:
                for event in self.agent.run():
                    self._send(event)
            except Exception as e:
                self._send({"type": "error", "message": str(e)})

        elif kind == "clear":
            self.agent.clear()
            self._send({"type": "cleared"})

        elif kind == "set_model":
            self.config.model = msg.get("model", self.config.model)
            self._init_provider()
            self._send({"type": "model_set", "model": self.config.model})

        elif kind == "set_provider":
            provider = msg.get("provider")
            if provider in FREE_PROVIDERS:
                self.config.provider = provider
                info = FREE_PROVIDERS[provider]
                self.config.model = msg.get("model", info["models"][0])
                self._init_provider()
                self._send({"type": "provider_set", "provider": provider, "model": self.config.model})
            else:
                self._send({"type": "error", "message": f"Unknown provider: {provider}"})

        elif kind == "status":
            available = False
            if self.provider:
                try:
                    available = self.provider.is_available()
                except Exception:
                    pass
            self._send({
                "type": "status",
                "provider": self.config.provider,
                "model": self.config.model,
                "available": available,
                "providers": list(FREE_PROVIDERS.keys()),
            })

        elif kind == "list_models":
            models = []
            if self.config.provider == "ollama" and self.provider:
                models = self.provider.list_models()
            else:
                info = FREE_PROVIDERS.get(self.config.provider, {})
                models = info.get("models", [])
            self._send({"type": "models", "models": models})

        elif kind == "ping":
            self._send({"type": "pong"})

        else:
            self._send({"type": "error", "message": f"Unknown message type: {kind}"})
