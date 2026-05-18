"""Agent loop: LLM ↔ tools cycle"""
import json
from .tools import TOOL_DEFINITIONS, run_tool


class Agent:
    def __init__(self, config, provider, on_token=None, on_tool_call=None, on_tool_result=None):
        self.config = config
        self.provider = provider
        self.on_token = on_token or (lambda t: None)
        self.on_tool_call = on_tool_call or (lambda n, a: None)
        self.on_tool_result = on_tool_result or (lambda n, r: None)
        self.messages = [
            {"role": "system", "content": config.system_prompt}
        ]

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def clear(self):
        self.messages = [{"role": "system", "content": self.config.system_prompt}]

    def run(self, max_iterations: int = 20):
        """Run agent loop until done or max_iterations reached. Yields events."""
        for iteration in range(max_iterations):
            # Collect full response
            full_content = ""
            tool_calls_raw = []

            for chunk in self.provider.chat(
                self.messages,
                tools=TOOL_DEFINITIONS,
                stream=True,
            ):
                content = chunk.get("content", "")
                if content:
                    full_content += content
                    self.on_token(content)
                    yield {"type": "token", "content": content}

                raw_calls = chunk.get("tool_calls", [])
                if raw_calls:
                    tool_calls_raw.extend(raw_calls)

            # Build assistant message
            assistant_msg = {"role": "assistant", "content": full_content}
            if tool_calls_raw:
                assistant_msg["tool_calls"] = tool_calls_raw
            self.messages.append(assistant_msg)

            # No tool calls → done
            if not tool_calls_raw:
                yield {"type": "done"}
                return

            # Execute tool calls
            tool_results = []
            for call in tool_calls_raw:
                # Normalize across Ollama / OpenAI formats
                if isinstance(call, dict):
                    fn = call.get("function", call)
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments", fn.get("parameters", {}))
                    call_id = call.get("id", f"call_{name}")
                else:
                    continue

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                else:
                    args = raw_args or {}

                self.on_tool_call(name, args)
                yield {"type": "tool_call", "name": name, "args": args}

                result = run_tool(name, args)

                self.on_tool_result(name, result)
                yield {"type": "tool_result", "name": name, "result": result}

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": result,
                })

            self.messages.extend(tool_results)

        yield {"type": "error", "content": "Max iterations reached."}
