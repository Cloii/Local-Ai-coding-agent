"""
cloii-cli — Personal AI coding agent with modern UI
Enhanced with Rich library for better UX and performance improvements
"""
import sys
import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from .config import FREE_PROVIDERS
from .providers import get_provider
from .agent import Agent
from .cli_ui import CLITheme, ProgressSpinner, console

# ── Help Text ─────────────────────────────────────────────────────────────────
HELP_TEXT = """
[bold cyan]Commands[/bold cyan]
────────────────────────────────────────
[cyan]/help[/cyan]               Show this help
[cyan]/provider [name][/cyan]    Switch provider
[cyan]/model [name][/cyan]       Switch model
[cyan]/models[/cyan]             List available models
[cyan]/status[/cyan]             Show config and connection
[cyan]/clear[/cyan]              Clear conversation
[cyan]/save [file][/cyan]        Save session (default: session.json)
[cyan]/load [file][/cyan]        Load session
[cyan]/cd [path][/cyan]          Change directory
[cyan]/pwd[/cyan]                Show current directory
[cyan]/exit[/cyan]               Quit

[bold cyan]Tools available to the agent[/bold cyan]
────────────────────────────────────────
[dim]bash[/dim]        Run shell commands
[dim]read_file[/dim]   Read any file
[dim]write_file[/dim]  Create or overwrite files
[dim]edit_file[/dim]   Find-and-replace in files
[dim]list_files[/dim]  Browse directories
[dim]web_fetch[/dim]   Fetch a web page
[dim]web_search[/dim]  Search DuckDuckGo (no key needed)
"""


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
            CLITheme.error(f"Provider init failed: {e}")

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        CLITheme.welcome("1.0.0", self.config.provider, self.config.model)
        while True:
            try:
                user_input = CLITheme.prompt(Path.cwd()).strip()
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

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
            console.print(Panel(HELP_TEXT, title="[bold cyan]Help[/bold cyan]", border_style="cyan"))

        elif c in ("/exit", "/quit"):
            sys.exit(0)

        elif c == "/clear":
            self.agent.clear()
            os.system("cls" if os.name == "nt" else "clear")
            CLITheme.welcome("1.0.0", self.config.provider, self.config.model)

        elif c == "/status":
            self._status()

        elif c == "/provider":
            if not arg:
                console.print(f"\n[cyan]Current:[/cyan] [bold]{self.config.provider}[/bold]\n")
                for k, info in FREE_PROVIDERS.items():
                    mark = "  ← active" if k == self.config.provider else ""
                    console.print(f"  [cyan]{k:<16}[/cyan] [dim]{info['description']}[/dim]{mark}")
                console.print()
            elif arg in FREE_PROVIDERS:
                self.config.provider = arg
                self.config.model = FREE_PROVIDERS[arg]["models"][0]
                self._init_provider()
                self.config.save()
                CLITheme.success(f"Switched to {arg} · {self.config.model}")
            else:
                CLITheme.error(f"Unknown provider '{arg}'. Options: {', '.join(FREE_PROVIDERS)}")

        elif c == "/model":
            if not arg:
                console.print(f"\n[cyan]Current:[/cyan] [bold]{self.config.model}[/bold]\n")
            else:
                self.config.model = arg
                self._init_provider()
                self.config.save()
                CLITheme.success(f"Model → {arg}")

        elif c == "/models":
            self._list_models()

        elif c == "/save":
            f = arg or "session.json"
            try:
                Path(f).write_text(json.dumps(self.agent.messages, indent=2, ensure_ascii=False))
                CLITheme.success(f"Saved → {f}")
            except Exception as e:
                CLITheme.error(f"Save failed: {e}")

        elif c == "/load":
            if not arg:
                CLITheme.error("Usage: /load <filename>")
            else:
                try:
                    msgs = json.loads(Path(arg).read_text())
                    self.agent.messages = msgs
                    CLITheme.success(f"Loaded {len(msgs)} messages from {arg}")
                except Exception as e:
                    CLITheme.error(f"Load failed: {e}")

        elif c == "/cd":
            if not arg:
                console.print(f"  [dim]{Path.cwd()}[/dim]")
            else:
                try:
                    os.chdir(arg)
                    CLITheme.success(str(Path.cwd()))
                except Exception as e:
                    CLITheme.error(str(e))

        elif c == "/pwd":
            console.print(f"  [dim]{Path.cwd()}[/dim]")

        else:
            CLITheme.error(f"Unknown command: {c} — try /help")

    def _status(self):
        """Display connection and configuration status"""
        available = False
        if self.provider:
            try:
                available = self.provider.is_available()
            except Exception:
                pass
        
        stat = "[green]✓ connected[/green]" if available else "[red]✗ offline[/red]"
        key = self.config.get_api_key()
        key_s = "[green]set[/green]" if key else "[yellow]not set[/yellow]"
        info = FREE_PROVIDERS.get(self.config.provider, {})
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="dim", width=12)
        table.add_column()
        
        table.add_row("provider", f"{self.config.provider}  [dim]{info.get('name', '')}[/dim]")
        table.add_row("model", self.config.model)
        table.add_row("status", stat)
        table.add_row("api key", key_s)
        table.add_row("directory", str(Path.cwd()))
        table.add_row("context", f"{len(self.agent.messages)} messages")
        
        console.print()
        console.print(table)
        console.print()

    def _list_models(self):
        """List available models for current provider"""
        info = FREE_PROVIDERS.get(self.config.provider, {})
        console.print(f"\n[cyan bold]{info.get('name', self.config.provider)}[/]")
        console.print(f"[dim]{info.get('description', '')}[/]")
        
        if self.config.provider == "ollama":
            installed = []
            if self.provider:
                try:
                    installed = self.provider.list_models()
                except Exception:
                    pass
            if installed:
                console.print(f"\n[cyan]Installed:[/cyan]")
                for m in installed:
                    mark = "  [green]✓[/green]" if m == self.config.model else ""
                    console.print(f"  [dim]{m}[/dim]{mark}")
            console.print(f"\n[cyan]Suggested[/cyan]  [dim](ollama pull <model>)[/dim]")
            for m in info.get("models", []):
                console.print(f"  [dim]{m}[/dim]")
        else:
            console.print(f"\n[cyan]Available:[/cyan]")
            for m in info.get("models", []):
                mark = "  [green]✓[/green]" if m == self.config.model else ""
                console.print(f"  [dim]{m}[/dim]{mark}")
        console.print()

    # ── Agent ─────────────────────────────────────────────────────────────────

    def _run_agent(self, user_input: str):
        """Run the agent with user input"""
        self.agent.on_tool_call = CLITheme.tool_call
        self.agent.on_tool_result = CLITheme.tool_result
        self.agent.add_user(user_input)

        console.print()

        in_code = False
        code_lang = ""
        code_buffer = ""

        try:
            with ProgressSpinner("Thinking"):
                first_token = True
                
                for event in self.agent.run():
                    t = event["type"]

                    if t == "token":
                        if first_token:
                            # Hide spinner on first token
                            first_token = False
                        
                        tok = event["content"]

                        if "```" in tok:
                            parts = tok.split("```")
                            for i, part in enumerate(parts):
                                if i % 2 == 0:
                                    # Regular text
                                    if in_code:
                                        code_buffer += part
                                    else:
                                        console.print(part, end="")
                                else:
                                    # Code block boundary
                                    if in_code:
                                        # End code block
                                        CLITheme.code_block(code_buffer, code_lang)
                                        code_buffer = ""
                                        in_code = False
                                    else:
                                        # Start code block
                                        code_lang = part.strip().split()[0] if part.strip() else ""
                                        in_code = True
                        else:
                            if in_code:
                                code_buffer += tok
                            else:
                                console.print(tok, end="")

                    elif t == "tool_call":
                        if in_code:
                            CLITheme.code_block(code_buffer, code_lang)
                            code_buffer = ""
                            in_code = False

                    elif t == "tool_result":
                        console.print()
                        in_code = False

                    elif t == "error":
                        CLITheme.error(event["content"])

                # Flush any remaining code block
                if in_code and code_buffer:
                    CLITheme.code_block(code_buffer, code_lang)

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted[/dim]")
        except Exception as e:
            CLITheme.error(f"Agent error: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()

        console.print()