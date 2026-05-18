"""OpenAI-compatible provider for Groq and OpenRouter free tiers"""
import json
import urllib.request
import urllib.error


class OpenAICompatProvider:
    def __init__(self, config):
        self.config = config
        from ..config import FREE_PROVIDERS
        info = FREE_PROVIDERS.get(config.provider, {})
        self.base_url = info.get("base_url", "")
        self.api_key = config.get_api_key()

    def is_available(self):
        return bool(self.api_key and self.base_url)

    def chat(self, messages, tools=None, stream=True):
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if "openrouter" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/Cloii/cloii-cli"
            headers["X-Title"] = "cloii-cli"

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if stream:
                    for line in resp:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            line = line[6:]
                        if line == "[DONE]" or not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "") or ""
                            tool_calls = delta.get("tool_calls", [])
                            finish = chunk["choices"][0].get("finish_reason")
                            yield {
                                "content": content,
                                "tool_calls": tool_calls,
                                "done": finish is not None,
                            }
                        except Exception:
                            continue
                else:
                    data = json.loads(resp.read())
                    msg = data["choices"][0]["message"]
                    yield {
                        "content": msg.get("content", "") or "",
                        "tool_calls": msg.get("tool_calls", []) or [],
                        "done": True,
                    }
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"API error {e.code}: {body}")
