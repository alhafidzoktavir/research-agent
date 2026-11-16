# Research Agent

[Bahasa Indonesia](README.id.md)

A command-line **AI research assistant**. Ask it a question and it plans its research, searches the web,
reads the most relevant pages, cross-checks sources, and writes a cited answer.
Substantial answers are also saved as Markdown reports.

```text
$ research-agent "How is Indonesia's nickel industry affecting EV battery prices?"

[search] Indonesia nickel production 2026 EV battery
[search] nickel price trend battery cost per kWh 2026
[fetch] https://www.iea.org/...
...
**Short answer:** ...

Sources
- https://...

[save_report] Report saved to reports/indonesia-nickel-ev-batteries.md

--- 5 searches, 3 pages fetched | tokens: 48,210 in (31,004 cached), 3,912 out ---
```

## Features

- **Agentic research loop.** The agent decides what to search, which pages to open, and when it has enough.
- **Web search and web fetch** as server-side tools. No extra search API keys needed.
- **Custom local tool** (`save_report`) that writes reports to `reports/`, with path sanitising so the model can't write anywhere else.
- **Streaming output.** You see the answer and each search as it happens.
- **Follow-up questions** in interactive mode. The conversation keeps its context.
- **Prompt caching** on the conversation to cut cost on multi-step research.
- **Automatic fallback** to another model if a request is declined.
- Answers in whatever language you ask in.

## How it works

```text
           ┌──────────────────────────────────────────────┐
 question  │  Language model                              │
 ────────► │   ├─ web_search   (server-side tool)         │
           │   ├─ web_fetch    (server-side tool)         │
           │   └─ save_report  ──► tool_use ──┐           │
           └──────────────────────────────────┼───────────┘
                     ▲                        ▼
                     │  tool_result   research_agent/tools.py
                     └─────────────── (writes reports/*.md)
```

The core loop lives in [`research_agent/agent.py`](research_agent/agent.py):

1. Stream the conversation to the model.
2. Server tools (search / fetch) run inside the same turn; their results come back in the response.
3. If the model calls `save_report`, validate the input, run it locally, and send back a `tool_result`.
4. Repeat until the model answers without calling a tool (with a safety cap on turns).

It also handles paused turns, declined requests, output-limit cut-offs, and malformed tool input.

## Getting started

**Requirements:** Python 3.10+ and an API key from [console.anthropic.com](https://console.anthropic.com/).

```bash
git clone https://github.com/alhafidzoktavir/research-agent.git
cd research-agent
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and put your API key in it. Never commit `.env` (it is already in `.gitignore`).

## Usage

```bash
# One question
research-agent "What are the main differences between solid-state and lithium-ion batteries?"

# Interactive mode, with follow-up questions
research-agent

# Without installing: python -m research_agent "..."
```

| Option | Default | Description |
| --- | --- | --- |
| `--model` | see `agent.py` | Model ID to use |
| `--effort` | `high` | `low` / `medium` / `high` / `xhigh` / `max`: thoroughness vs. cost |
| `--max-searches` | `8` | Web searches allowed per request |
| `--max-fetches` | `6` | Pages fetched per request |
| `--reports-dir` | `reports` | Where reports are saved |
| `--no-save` | off | Don't save reports to disk |
| `--show-thinking` | off | Print a summary of the model's reasoning |

### Use it from Python

```python
from research_agent import AgentConfig, ResearchAgent

agent = ResearchAgent(config=AgentConfig(effort="medium", save_reports=False))
answer = agent.ask("Summarise the latest research on microplastics in drinking water.")
follow_up = agent.ask("Which of those studies were done in Southeast Asia?")
```

## Cost note

Each question makes several API calls, plus web search usage. Lower `--effort`, `--max-searches`,
and `--max-fetches` to keep costs down.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests cover the local tool and its input validation, and run offline without an API key.
CI runs them on every push (see `.github/workflows/tests.yml`).

## Project structure

```text
research_agent/
├── agent.py     # the agent loop (streaming, tool handling, stop reasons)
├── tools.py     # local tools: save_report + validation
├── prompts.py   # system prompt
└── cli.py       # command-line interface
tests/
└── test_tools.py
```

## License

[MIT](LICENSE)
