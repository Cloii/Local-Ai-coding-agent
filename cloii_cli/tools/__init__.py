"""Built-in tools for cloii-cli agent"""
import os
import subprocess
import urllib.request
import urllib.parse
import json
import re
from pathlib import Path

# ─── Security ────────────────────────────────────────────────────────────────

BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/",
    r":(){ :|:& };:",  # fork bomb
    r"dd\s+if=",
    r"mkfs\.",
    r"> /dev/sd",
    r"chmod\s+-R\s+777\s+/",
    r"wget.+\|\s*sh",
    r"curl.+\|\s*sh",
]

def _is_dangerous(cmd: str) -> bool:
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, cmd):
            return True
    return False

# ─── Tool definitions (OpenAI function calling format) ───────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command and return stdout/stderr. Use for running code, installing packages, git commands, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file with new content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific string in a file with new content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to edit"},
                    "old_str": {"type": "string", "description": "Exact string to find and replace"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current dir)", "default": "."},
                    "pattern": {"type": "string", "description": "Glob pattern e.g. *.py"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and return the text content of a web page",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo and return results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]

# ─── Tool implementations ─────────────────────────────────────────────────────

def tool_bash(command: str, timeout: int = 30) -> str:
    if _is_dangerous(command):
        return "ERROR: Blocked dangerous command."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        out = result.stdout or ""
        err = result.stderr or ""
        code = result.returncode
        output = ""
        if out:
            output += out
        if err:
            output += f"\n[stderr]\n{err}"
        output += f"\n[exit code: {code}]"
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"


def tool_read_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"ERROR: File not found: {path}"
        if p.stat().st_size > 1_000_000:
            return "ERROR: File too large (>1MB). Use bash with head/tail."
        content = p.read_text(errors="replace")
        lines = content.splitlines()
        numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
        return f"File: {path} ({len(lines)} lines)\n\n{numbered}"
    except Exception as e:
        return f"ERROR: {e}"


def tool_write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"ERROR: {e}"


def tool_edit_file(path: str, old_str: str, new_str: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"ERROR: File not found: {path}"
        content = p.read_text(errors="replace")
        if old_str not in content:
            return f"ERROR: String not found in {path}"
        count = content.count(old_str)
        if count > 1:
            return f"ERROR: Found {count} matches. Make old_str more specific."
        new_content = content.replace(old_str, new_str, 1)
        p.write_text(new_content)
        return f"Edited {path} successfully."
    except Exception as e:
        return f"ERROR: {e}"


def tool_list_files(path: str = ".", pattern: str = None) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"ERROR: Path not found: {path}"
        if pattern:
            files = list(p.glob(pattern))
        else:
            files = list(p.iterdir())
        files.sort()
        lines = []
        for f in files[:200]:
            kind = "DIR " if f.is_dir() else "FILE"
            size = f.stat().st_size if f.is_file() else 0
            lines.append(f"{kind} {f.name:<40} {size:>10} bytes")
        result = "\n".join(lines)
        if len(files) > 200:
            result += f"\n... and {len(files)-200} more"
        return result or "(empty)"
    except Exception as e:
        return f"ERROR: {e}"


def tool_web_fetch(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 cloii-cli/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read(500_000)
            text = raw.decode("utf-8", errors="replace")
            # Strip HTML tags
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s{3,}", "\n\n", text)
            text = text.strip()
            return text[:8000] + ("\n...[truncated]" if len(text) > 8000 else "")
    except Exception as e:
        return f"ERROR: {e}"


def tool_web_search(query: str, num_results: int = 5) -> str:
    try:
        # DuckDuckGo instant answer API (no key needed)
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1"
        headers = {"User-Agent": "cloii-cli/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        results = []
        # Abstract / instant answer
        if data.get("AbstractText"):
            results.append(f"[Summary] {data['AbstractText']}\nSource: {data.get('AbstractURL','')}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                url_link = topic.get("FirstURL", "")
                results.append(f"• {topic['Text']}\n  {url_link}")

        if not results:
            # Fallback: HTML scrape DuckDuckGo
            url2 = f"https://html.duckduckgo.com/html/?q={encoded}"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                html = resp2.read().decode("utf-8", errors="replace")
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
            urls = re.findall(r'class="result__url"[^>]*>(.*?)</span>', html, re.DOTALL)
            for i in range(min(num_results, len(snippets))):
                title = re.sub(r"<[^>]+>", "", titles[i] if i < len(titles) else "")
                snippet = re.sub(r"<[^>]+>", "", snippets[i])
                link = urls[i].strip() if i < len(urls) else ""
                results.append(f"[{i+1}] {title}\n    {snippet}\n    {link}")

        return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"ERROR searching: {e}"


# ─── Dispatcher ───────────────────────────────────────────────────────────────

TOOL_MAP = {
    "bash": tool_bash,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "list_files": tool_list_files,
    "web_fetch": tool_web_fetch,
    "web_search": tool_web_search,
}


def run_tool(name: str, args: dict) -> str:
    fn = TOOL_MAP.get(name)
    if not fn:
        return f"ERROR: Unknown tool: {name}"
    try:
        return fn(**args)
    except TypeError as e:
        return f"ERROR calling {name}: {e}"
