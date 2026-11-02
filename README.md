![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=blue)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![PDF](https://img.shields.io/badge/PDF-ReportLab-CC0000)
[![CI](https://img.shields.io/github/actions/workflow/status/SKR-35/Word-Search-Puzzle-Generator/ci.yml?branch=master&label=CI&logo=githubactions&logoColor=white)](https://github.com/SKR-35/Word-Search-Puzzle-Generator/actions/workflows/ci.yml)
  

# Word Search Puzzle Generator

**Generate reproducible, quality-scored word search puzzles from themed word lists.**

A Python command-line tool for creating word search grids, evaluating placement quality, storing puzzles in SQLite and exporting printable puzzle and solution PDFs. Supply one or more topics in a text file; the generator handles placement, validation, scoring and export.

## Features

- **Eight search directions:** horizontal, vertical and diagonal, forwards or backwards.
- **Configurable square grids:** 15 × 15, 20 × 20 (default) or 25 × 25.
- **Multiple topics per input:** one puzzle per topic, with exactly 15 words each.
- **Deterministic generation:** a seed makes candidate generation reproducible.
- **Quality-gated selection:** evaluate multiple candidates and reject results below a configurable threshold.
- **Placement diagnostics:** spatial entropy, direction diversity, spatial coverage, intersection quality and placement balance.
- **Informational difficulty estimates:** a 0–100 rating and four difficulty categories, separate from placement quality.
- **SQLite persistence:** retain grids, word placements, instructions, quality metrics and solution data; avoid duplicate records.
- **PDF export:** one puzzle per US Letter page and up to four highlighted solutions per page.

## Quick start

Requires **Python 3.12** and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```powershell
uv sync
uv run word-search examples/input.txt --size 20 --seed 42 --min-quality 80 --candidates 100
```

This generates terminal previews without writing to the database.

To persist puzzles and export PDFs:

```powershell
uv run word-search examples/input.txt --size 20 --seed 42 --min-quality 80 --candidates 100 --db data/puzzles.db --pdf-dir output
```

Generated files:

```text
data/puzzles.db
output/word-search-puzzles.pdf
output/word-search-solutions.pdf
```

The PDF export reads the saved puzzle records, so the exported solutions correspond to the persisted grids. Re-running identical generation inputs reuses existing records instead of inserting duplicates.

## Input format

Create a UTF-8 text file with a `topic:` heading followed by **exactly 15 words or phrases**. Repeat the block to generate additional puzzles.

```text
topic: Ancient Greek Philosophy
SOCRATES
PLATO
ARISTOTLE
LOGOS
ETHICS
VIRTUE
REASON
DIALECTIC
ACADEMY
STOICISM
ATOMISM
COSMOS
SOPHIST
EPISTEME
METAPHYSICS

topic: Existentialism
SARTRE
CAMUS
KIERKEGAARD
FREEDOM
ABSURD
EXISTENCE
ESSENCE
CHOICE
ANGST
AUTHENTICITY
DESPAIR
ALIENATION
NOTHINGNESS
SUBJECTIVITY
RESPONSIBILITY
```

Blank lines and `#` comments are supported. The generator uses the English alphabet (`A–Z`); words are normalized for placement while their original input forms are retained for display and storage. Input is validated before generation.

## Command-line options

| Option | Purpose | Default |
| --- | --- | --- |
| `input` | Path to the themed word-list file | Required |
| `--size` | Square grid dimension | `20` |
| `--seed` | Seed for reproducible generation | `42` |
| `--min-quality` | Minimum accepted placement-quality score (0–100) | `80` |
| `--candidates` | Number of candidate boards to evaluate | `100` |
| `--db` | SQLite database path; enables persistence | Preview only |
| `--pdf-dir` | Directory for puzzle and solution PDFs; requires `--db` | Disabled |

Example using a smaller grid:

```powershell
uv run word-search examples/input.txt --size 15 --seed 123 --candidates 200
```

If no candidate satisfies the quality threshold, generation fails rather than silently accepting a lower-quality puzzle. Some word lists may be infeasible for a given grid size.

## How quality evaluation works

Each valid candidate receives a **placement-quality score from 0 to 100**, based on five weighted components:

| Component | Weight | What it measures |
| --- | ---: | --- |
| Spatial entropy | 35% | Distribution of placed word cells across board regions |
| Direction diversity | 25% | Variety of placement directions |
| Spatial coverage | 20% | Use of different areas of the grid |
| Intersection quality | 10% | Shared letters across words |
| Placement balance | 10% | Concentration and positional balance |

The generator selects the highest-scoring valid candidate from its search and applies the minimum-quality gate. **Quality scores and difficulty ratings are heuristics**, not validated measures of human solving time or guaranteed visual appeal. Review print samples before publication.

## Data and exports

SQLite stores the generated grid and enough metadata to recover its solution without regenerating it: topic, original words, placements and directions, quality components, instructions and difficulty information. Duplicate detection helps prevent identical puzzles from being stored repeatedly.

PDF export produces:

- **Puzzle pages:** one grid per US Letter (8.5 × 11 in) page, with topic, instructions and a word list.
- **Solution pages:** up to four grids per page, with highlighted answer paths.

PDF layout is intended for printable review; final print-production compliance, margins and proofing remain the responsibility of the publishing workflow.

## Development

Run the automated checks:

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

The implementation separates parsing, puzzle generation, quality evaluation, database persistence and PDF rendering into focused modules under `src/word_search_generator/`.