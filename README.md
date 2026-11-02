# Word Search Puzzle Generator

Phase 1: deterministic, eight-direction word search previews with multi-topic text input.

## Setup (Windows PowerShell)

Install uv if needed: https://docs.astral.sh/uv/getting-started/installation/

```powershell
uv sync
uv run word-search examples/input.txt --size 20 --seed 42
uv run pytest -q
```

`--size` defaults to 20. Try 15 or 25. Every `topic:` starts a new puzzle; exactly 15 words per topic. Blank lines and `#` comments are allowed.

**Not yet production-ready:** Phase 1 does not calculate a quality score, save SQLite records or export PDFs. These are planned for later phases. Do not use Phase 1 previews for publication without manual verification.

## Phase 2 — quality-gated previews

```powershell
uv sync
uv run pytest -q
uv run word-search examples/input.txt --size 20 --seed 42 --min-quality 80 --candidates 100
```

The CLI searches deterministic candidate boards and reports a 0–100 placement-quality score, component metrics and an informational difficulty rating. If no candidate meets the threshold, it exits with an error rather than outputting an inferior board. This is still a preview: **SQLite persistence and PDF export are not implemented**. The score is a heuristic and its weights/threshold need calibration on actual print samples.
