"""Ollama local provider"""
import json
import urllib.request
import urllib.error


class OllamaProvider:
    def __init__(self, config):
        self.config = config
        self.host = config.ollama_host

    def is_available(self):
        try:
            req = urllib.request.urlopen(f"{self.host}/api/tags", timeout=3)
            return req.status == 200
        except Exception:
            return False

    def list_models(self):
        try:
            req = urllib.request.urlopen(f"{self.host}/api/tags", timeout=5)
            data = json.loads(req.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def chat(self, messages, tools=None, stream=True):
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "options": {"num_predict": self.config.max_tokens},
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            if stream:
                for line in resp:
                    line = line.decode().strip()
                    if line:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        content = msg.get("content", "")
                        tool_calls = msg.get("tool_calls", [])
                        done = chunk.get("done", False)
                        yield {"content": content, "tool_calls": tool_calls, "done": done}
            else:
                data = json.loads(resp.read())
                yield {
                    "content": data.get("message", {}).get("content", ""),
                    "tool_calls": data.get("message", {}).get("tool_calls", []),
                    "done": True,
                }
