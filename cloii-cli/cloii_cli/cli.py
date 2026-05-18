"""
cloii-cli — Claude Code-style terminal interface
"""
import sys
import os
import json
import shutil
import time
import threading
from pathlib import Path
from .config import FREE_PROVIDERS
from .providers import get_provider
from .agent import Agent

# ── ANSI ──────────────────────────────────────────────────────────────────────
R      = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[96m"
GCYAN  = "\033[36m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
WHITE  = "\033[97m"
BLUE   = "\033[94m"
GRAY   = "\033[90m"

# ── Helpers ───────────────────────────────────────────────────────────────────
def tw():
    return shutil.get_terminal_size((100, 24)).columns

def rule(char="─", color=GRAY, width=None):
    w = width or tw()
    return f"{color}{char * w}{R}"

# ── Welcome ───────────────────────────────────────────────────────────────────
LOGO = [
    " ███╗   ███╗██╗   ██╗        ██████╗██╗     ██╗",
    " ████╗ ████║╚██╗ ██╔╝       ██╔════╝██║     ██║",
    " ██╔████╔██║ ╚████╔╝        ██║     ██║     ██║",
    " ██║╚██╔╝██║  ╚██╔╝         ██║     ██║     ██║",
    " ██║ ╚═╝ ██║   ██║          ╚██████╗███████╗██║",
    " ╚═╝     ╚═╝   ╚═╝           ╚═════╝╚══════╝╚═╝",
]

def print_welcome(config):
    print()
    for line in LOGO:
        print(f"  {CYAN}{BOLD}{line}{R}")
    print()
    print(f"  {BOLD}Personal AI Coding Agent{R}  {GRAY}v1.0.0{R}")
    print(f"  {GRAY}{rule('─', GRAY, 34)}{R}")
    pinfo = FREE_PROVIDERS.get(config.provider, {})
    print(f"  {GRAY}provider {R} {CYAN}{config.provider}{R}  {GRAY}{pinfo.get('name','')}{R}")
    print(f"  {GRAY}model    {R} {CYAN}{config.model}{R}")
    print(f"  {GRAY}cwd      {R} {GRAY}{Path.cwd()}{R}")
    print()
    print(f"  {GRAY}Type {WHITE}/help{GRAY} for commands · Ctrl+C to exit{R}")
    print()

HELP_TEXT = f"""
  {BOLD}{CYAN}Commands{R}
  {"─"*40}
  {WHITE}/help{R}               Show this help
  {WHITE}/provider [name]{R}    Switch provider  {GRAY}ollama · groq · openrouter{R}
  {WHITE}/model [name]{R}       Switch model
  {WHITE}/models{R}             List available models
  {WHITE}/status{R}             Show config and connection
  {WHITE}/clear{R}              Clear conversation
  {WHITE}/save [file]{R}        Save session  {GRAY}(default: session.json){R}
  {WHITE}/load [file]{R}        Load session
  {WHITE}/cd [path]{R}          Change directory
  {WHITE}/pwd{R}                Show current directory
  {WHITE}/exit{R}               Quit

  {BOLD}{CYAN}Agent tools{R}
  {"─"*40}
  {GRAY}bash{R}        Run shell commands
  {GRAY}read_file{R}   Read any file
  {GRAY}write_file{R}  Create or overwrite files
  {GRAY}edit_file{R}   Find-and-replace in files
  {GRAY}list_files{R}  Browse directories
  {GRAY}web_fetch{R}   Fetch a web page
  {GRAY}web_search{R}  Search DuckDuckGo (no key needed)
"""

# ── Spinner ───────────────────────────────────────────────────────────────────
FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

class Spinner:
    def __init__(self, label="Thinking"):
        self.label = label
        self._i = 0
        self._active = False
        self._t = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._active = True
        self._t.start()

    def stop(self):
        self._active = False
        self._t.join(timeout=0.3)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _loop(self):
        while self._active:
            f = FRAMES[self._i % len(FRAMES)]
            sys.stdout.write(f"\r  {CYAN}{f}{R} {GRAY}{self.label}…{R}")
            sys.stdout.flush()
            self._i += 1
            time.sleep(0.08)

# ── CLI ───────────────────────────────────────────────────────────────────────
class CLI:
    def __init__(self, config):
        self.config = config
        self.provider = None
        self.agent = None
        self._init_provider()
        self._setup_readline()

    def _setup_readline(self):
        try:
            import readline
            import atexit
            h = Path.home() / ".cloii_history"
            try:
                readline.read_history_file(h)
            except FileNotFoundError:
                pass
            readline.set_history_length(500)
            atexit.register(readline.write_history_file, h)
        except ImportError:
            pass

    def _init_provider(self):
        try:
            self.provider = get_provider(self.config)
            self.agent = Agent(self.config, self.provider)
        except Exception as e:
            self._err(f"Provider init failed: {e}")

    # ── Output ────────────────────────────────────────────────────────────────

    def _err(self, msg):
        print(f"\n  {RED}✗{R} {msg}\n")

    def _ok(self, msg):
        print(f"  {GREEN}✓{R} {msg}")

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _prompt(self) -> str:
        cwd = Path.cwd()
        try:
            rel = cwd.relative_to(Path.home())
            path_str = f"~/{rel}"
        except ValueError:
            path_str = str(cwd)
        # Claude Code-style two-line prompt
        prompt = f"\n{GRAY}┌ {R}{WHITE}{path_str}{R} {GRAY}({self.config.provider}/{self.config.model.split(':')[0]}){R}\n{GRAY}└▶{R} "
        return input(prompt)

    # ── Tool display ──────────────────────────────────────────────────────────

    TOOL_ICONS = {
        "bash":       ("⬡", YELLOW),
        "read_file":  ("⊞", BLUE),
        "write_file": ("⊟", GREEN),
        "edit_file":  ("✎", CYAN),
        "list_files": ("≡", GRAY),
        "web_fetch":  ("⊕", CYAN),
        "web_search": ("⊕", CYAN),
    }

    def _show_tool_call(self, name, args):
        icon, color = self.TOOL_ICONS.get(name, ("•", GRAY))
        # First arg value as preview
        main_arg = ""
        if args:
            v = next(iter(args.values()), "")
            if isinstance(v, str):
                main_arg = v[:72] + ("…" if len(v) > 72 else "")
        print(f"\n  {color}{icon} {BOLD}{name}{R}  {GRAY}{main_arg}{R}")

    def _show_tool_result(self, name, result):
        lines = result.strip().splitlines()
        for line in lines[:8]:
            print(f"    {GRAY}│ {DIM}{line[:96]}{R}")
        if len(lines) > 8:
            print(f"    {GRAY}│ … +{len(lines)-8} more lines{R}")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        print_welcome(self.config)
        while True:
            try:
                raw = self._prompt()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n  {GRAY}Goodbye!{R}\n")
                break

            user_input = raw.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                self._handle_slash(user_input)
            else:
                self._run_agent(user_input)

    # ── Slash commands ────────────────────────────────────────────────────────

    def _handle_slash(self, cmd: str):
        parts = cmd.split(None, 1)
        c = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if c == "/help":
            print(HELP_TEXT)

        elif c in ("/exit", "/quit"):
            print(f"\n  {GRAY}Goodbye!{R}\n")
            sys.exit(0)

        elif c == "/clear":
            self.agent.clear()
            os.system("cls" if os.name == "nt" else "clear")
            print_welcome(self.config)
            self._ok("Conversation cleared")

        elif c == "/status":
            self._status()

        elif c == "/provider":
            if not arg:
                print(f"\n  {BOLD}Current:{R} {CYAN}{self.config.provider}{R}")
                print(f"\n  {BOLD}Available:{R}")
                for k, info in FREE_PROVIDERS.items():
                    mark = f"  {GREEN}← active{R}" if k == self.config.provider else ""
                    print(f"    {WHITE}{k:<14}{R}{GRAY}{info['description']}{R}{mark}")
                print()
            elif arg in FREE_PROVIDERS:
                self.config.provider = arg
                self.config.model = FREE_PROVIDERS[arg]["models"][0]
                self._init_provider()
                self.config.save()
                self._ok(f"Switched to {CYAN}{arg}{R} · model: {CYAN}{self.config.model}{R}")
            else:
                self._err(f"Unknown provider '{arg}'. Options: {', '.join(FREE_PROVIDERS)}")

        elif c == "/model":
            if not arg:
                print(f"\n  {BOLD}Current:{R} {CYAN}{self.config.model}{R}\n")
            else:
                self.config.model = arg
                self._init_provider()
                self.config.save()
                self._ok(f"Model → {CYAN}{arg}{R}")

        elif c == "/models":
            self._list_models()

        elif c == "/save":
            f = arg or "session.json"
            try:
                Path(f).write_text(json.dumps(self.agent.messages, indent=2, ensure_ascii=False))
                self._ok(f"Saved → {f}")
            except Exception as e:
                self._err(f"Save failed: {e}")

        elif c == "/load":
            if not arg:
                self._err("Usage: /load <filename>")
            else:
                try:
                    msgs = json.loads(Path(arg).read_text())
                    self.agent.messages = msgs
                    self._ok(f"Loaded {len(msgs)} messages from {arg}")
                except Exception as e:
                    self._err(f"Load failed: {e}")

        elif c == "/cd":
            if not arg:
                print(f"  {Path.cwd()}")
            else:
                try:
                    os.chdir(arg)
                    self._ok(str(Path.cwd()))
                except Exception as e:
                    self._err(str(e))

        elif c == "/pwd":
            print(f"  {Path.cwd()}")

        else:
            self._err(f"Unknown command: {c}  — try /help")

    def _status(self):
        available = False
        if self.provider:
            try:
                available = self.provider.is_available()
            except Exception:
                pass
        stat = f"{GREEN}● connected{R}" if available else f"{RED}● offline{R}"
        key = self.config.get_api_key()
        key_s = f"{GREEN}set{R}" if key else f"{YELLOW}not set{R}"
        info = FREE_PROVIDERS.get(self.config.provider, {})
        print()
        for label, val in [
            ("provider",  f"{CYAN}{self.config.provider}{R}  {GRAY}({info.get('name','')}){R}"),
            ("model",     f"{CYAN}{self.config.model}{R}"),
            ("status",    stat),
            ("api key",   key_s),
            ("directory", f"{GRAY}{Path.cwd()}{R}"),
            ("context",   f"{GRAY}{len(self.agent.messages)} messages{R}"),
        ]:
            print(f"  {GRAY}{label:<12}{R} {val}")
        print()

    def _list_models(self):
        info = FREE_PROVIDERS.get(self.config.provider, {})
        print(f"\n  {BOLD}{info.get('name', self.config.provider)}{R}  {GRAY}{info.get('description','')}{R}")
        print(f"  {GRAY}{'─'*48}{R}")
        if self.config.provider == "ollama":
            installed = []
            if self.provider:
                try:
                    installed = self.provider.list_models()
                except Exception:
                    pass
            if installed:
                print(f"\n  {BOLD}Installed:{R}")
                for m in installed:
                    mark = f"  {GREEN}✓{R}" if m == self.config.model else ""
                    print(f"    {WHITE}{m}{R}{mark}")
            print(f"\n  {BOLD}Suggested:{R}  {GRAY}(ollama pull <model>){R}")
            for m in info.get("models", []):
                print(f"    {GRAY}{m}{R}")
        else:
            print(f"\n  {BOLD}Free models:{R}")
            for m in info.get("models", []):
                mark = f"  {GREEN}✓ active{R}" if m == self.config.model else ""
                print(f"    {WHITE}{m}{R}{mark}")
        print()

    # ── Agent ─────────────────────────────────────────────────────────────────

    def _run_agent(self, user_input: str):
        self.agent.on_tool_call = self._show_tool_call
        self.agent.on_tool_result = self._show_tool_result
        self.agent.add_user(user_input)

        w = tw()
        # Assistant header — like Claude Code's "Claude" label with rule
        print(f"\n  {CYAN}{BOLD}cloii{R}  {GRAY}{'─' * max(0, w - 9)}{R}\n")

        had_content = False
        in_code = False

        try:
            for event in self.agent.run():
                t = event["type"]

                if t == "token":
                    tok = event["content"]
                    had_content = True

                    # Detect code fence toggling
                    if "```" in tok:
                        parts = tok.split("```")
                        for i, part in enumerate(parts):
                            if i % 2 == 0:
                                # Normal text
                                self._write_text(part, in_code)
                            else:
                                # Fence boundary
                                in_code = not in_code
                                lang = part.strip() if not in_code is False else ""
                                if in_code:
                                    print(f"\n  {GRAY}```{lang}{R}")
                                else:
                                    print(f"  {GRAY}```{R}\n")
                    else:
                        self._write_text(tok, in_code)

                elif t == "tool_call":
                    if had_content:
                        print()
                    had_content = False

                elif t == "tool_result":
                    # Resume response header
                    print(f"\n  {CYAN}{BOLD}cloii{R}  {GRAY}{'─' * max(0, w - 9)}{R}\n")
                    had_content = False
                    in_code = False

                elif t == "error":
                    self._err(event["content"])

        except KeyboardInterrupt:
            print(f"\n\n  {YELLOW}⚠{R}  {GRAY}Interrupted{R}")
        except Exception as e:
            self._err(f"Agent error: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()

        # Bottom rule
        print(f"\n\n  {GRAY}{'─' * max(0, w - 2)}{R}\n")

    def _write_text(self, tok: str, in_code: bool):
        """Write a token to stdout, handling newline indentation."""
        if in_code:
            color = GCYAN = "\033[36m"
            sys.stdout.write(f"\033[36m{tok}\033[0m")
        else:
            # Indent continuation lines
            out = tok.replace("\n", "\n  ")
            sys.stdout.write(out)
        sys.stdout.flush()