# Contributing

Thank you for helping improve RDT.

## Verification

Create a virtual environment and install the test, build, and MCP dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m pip install -e '.[dev,mcp]'
python -m pytest
python -m build
python scripts/smoke_wheel.py dist/*.whl
```

CI runs the source suite on Python 3.10 and 3.14 and builds both an sdist and
wheel on Python 3.14. The wheel smoke check installs into a disposable environment
outside the checkout and needs network access for dependencies. Tests mock
external processes; they do not require Docker or verify a real Docker daemon.

## Language for Code and Internal Documentation

English is the default language for contributor-facing and agent-facing project
content, including:

- source-code comments
- docstrings
- inline developer notes
- MCP/server instructions and other AI-agent-facing prompts
- tests and other internal developer documentation

Localized user-facing resources should remain in their dedicated locations, such
as `rdt/locales/ru.json` or `docs/ru/`. Avoid mixing translated UI/docs content
into source-code comments or internal implementation notes.
