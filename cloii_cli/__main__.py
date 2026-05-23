"""cloii-cli: Personal AI coding agent CLI by Cloii"""
import sys
import argparse
from .cli import CLI
from .config import Config


def main():
    parser = argparse.ArgumentParser(
        prog="cloii",
        description="cloii-cli — Personal AI coding agent"
    )
    parser.add_argument("--model", default=None, help="Model to use")
    parser.add_argument("--provider", default=None, help="Provider: ollama, groq, openrouter")
    parser.add_argument("--debug", action="store_true", help="Debug output")
    parser.add_argument("--server", action="store_true", help="JSON server mode for desktop GUI")
    args = parser.parse_args()

    config = Config()
    if args.model:
        config.model = args.model
    if args.provider:
        config.provider = args.provider
    if args.debug:
        config.debug = True

    if args.server:
        from .server import Server
        Server(config).run()
    else:
        CLI(config).run()


if __name__ == "__main__":
    main()
