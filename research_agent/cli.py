"""Command-line interface.

    research-agent "What are the latest developments in solid-state batteries?"
    research-agent            # interactive mode with follow-up questions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anthropic

from . import __version__
from .agent import DEFAULT_MODEL, AgentConfig, ResearchAgent

EXIT_COMMANDS = {"exit", "quit", "q", ":q"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="A web research assistant powered by Claude.",
    )
    parser.add_argument("question", nargs="*", help="Question to research (omit for interactive mode).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL}).")
    parser.add_argument(
        "--effort",
        default="high",
        choices=["low", "medium", "high", "xhigh", "max"],
        help="How hard Claude thinks; higher is more thorough and costs more (default: high).",
    )
    parser.add_argument("--max-searches", type=int, default=8, help="Web searches allowed per request (default: 8).")
    parser.add_argument("--max-fetches", type=int, default=6, help="Pages fetched per request (default: 6).")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Where reports are saved.")
    parser.add_argument("--no-save", action="store_true", help="Do not save reports to disk.")
    parser.add_argument("--show-thinking", action="store_true", help="Print a summary of Claude's reasoning.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def print_usage(agent: ResearchAgent) -> None:
    u = agent.usage
    print(
        f"\n\n--- {u.searches} searches, {u.fetches} pages fetched | "
        f"tokens: {u.input_tokens:,} in ({u.cache_read_tokens:,} cached), {u.output_tokens:,} out ---"
    )


def main(argv: list[str] | None = None) -> int:
    # Windows consoles may default to a legacy code page; avoid crashes on
    # non-ASCII text in answers.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:  # optional: load ANTHROPIC_API_KEY from a .env file
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    args = parse_args(argv)
    config = AgentConfig(
        model=args.model,
        effort=args.effort,
        max_searches=args.max_searches,
        max_fetches=args.max_fetches,
        reports_dir=args.reports_dir,
        save_reports=not args.no_save,
        show_thinking=args.show_thinking,
    )
    agent = ResearchAgent(config=config)

    try:
        if args.question:
            agent.ask(" ".join(args.question))
            print_usage(agent)
            return 0

        print("Research Agent - ask a question (type 'exit' to quit).")
        while True:
            try:
                question = input("\n> ").strip()
            except EOFError:
                break
            if not question:
                continue
            if question.lower() in EXIT_COMMANDS:
                break
            agent.ask(question)
            print_usage(agent)
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except anthropic.AuthenticationError:
        print(
            "\nAuthentication failed. Set ANTHROPIC_API_KEY (see .env.example) "
            "or run `ant auth login`.",
            file=sys.stderr,
        )
        return 1
    except anthropic.RateLimitError:
        print("\nRate limited by the API. Wait a moment and try again.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as exc:
        print(f"\nAPI error ({exc.status_code}): {exc.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("\nCould not reach the Anthropic API. Check your internet connection.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
