"""
Enhanced CLI UI with Rich library
Provides modern, user-friendly terminal interface
"""
import sys
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Prompt
from rich.layout import Layout
from rich.spinner import Spinner
from rich.style import Style
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

# ── Rich Console ──────────────────────────────────────────────────────────────
console = Console()
err_console = Console(stderr=True)

# ── Theme Colors ──────────────────────────────────────────────────────────────
THEME = {
    "primary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "dim": "dim white",
    "code": "blue",
}


class CLITheme:
    """Modern, clean CLI theme"""
    
    @staticmethod
    def welcome(version: str, provider: str, model: str):
        """Display welcome banner"""
        title = Text("cloii", style=f"bold {THEME['primary']}")
        version_text = Text(f"v{version}", style=THEME["dim"])
        
        panel = Panel(
            f"{title}  {version_text}\n"
            f"[{THEME['dim']}]{provider} · {model}[/]\n"
            f"[{THEME['dim']}]Use [bold]/help[/] for commands[/]",
            border_style=THEME["primary"],
            padding=(1, 2),
        )
        console.print(panel)
    
    @staticmethod
    def error(message: str):
        """Display error message"""
        console.print(f"\n[{THEME['error']}]✗[/] {message}\n", style=f"{THEME['error']}")
    
    @staticmethod
    def success(message: str):
        """Display success message"""
        console.print(f"[{THEME['success']}]✓[/] {message}")
    
    @staticmethod
    def info(message: str):
        """Display info message"""
        console.print(f"[{THEME['dim']}]ℹ[/] {message}")
    
    @staticmethod
    def code_block(code: str, language: str = ""):
        """Display syntax-highlighted code block"""
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                try:
                    lexer = guess_lexer(code)
                except ClassNotFound:
                    lexer = get_lexer_by_name("text")
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
        
        syntax = Syntax(code, lexer.name.lower(), theme="monokai", line_numbers=False)
        console.print(syntax)
    
    @staticmethod
    def spinner(label: str = "Processing"):
        """Return a spinner for long operations"""
        return console.status(f"[{THEME['primary']}]{label}…[/]", spinner="dots")
    
    @staticmethod
    def tool_call(name: str, args: Dict[str, Any]):
        """Display tool call"""
        args_str = ""
        if args:
            main_arg = next(iter(args.values()), "")
            if isinstance(main_arg, str) and main_arg:
                args_str = f"  [dim]{main_arg[:100]}{'…' if len(main_arg) > 100 else ''}[/]"
        
        console.print(f"\n[{THEME['dim']}]→ {name}[/]{args_str}")
    
    @staticmethod
    def tool_result(name: str, result: str):
        """Display tool result"""
        lines = result.strip().splitlines()
        for line in lines[:8]:
            console.print(f"  [dim]{line[:100]}[/]")
        if len(lines) > 8:
            console.print(f"  [dim]… +{len(lines) - 8} lines[/]")
    
    @staticmethod
    def prompt(directory: Optional[Path] = None) -> str:
        """Get user input with styled prompt"""
        if directory is None:
            directory = Path.cwd()
        
        try:
            rel = directory.relative_to(Path.home())
            path_str = f"~/{rel}"
        except ValueError:
            path_str = str(directory)
        
        prompt_text = Text(f"{path_str} ", style=f"bold {THEME['primary']}")
        prompt_text.append(Text("> ", style=THEME["dim"]))
        
        return Prompt.ask(prompt=prompt_text, console=console)


class ProgressSpinner:
    """Async-safe spinner for progress indication"""
    
    def __init__(self, label: str = "Processing"):
        self.label = label
        self._status = None
    
    def start(self):
        """Start the spinner"""
        self._status = console.status(f"[{THEME['primary']}]{self.label}…[/]", spinner="dots")
        self._status.start()
    
    def stop(self):
        """Stop the spinner"""
        if self._status:
            self._status.stop()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
