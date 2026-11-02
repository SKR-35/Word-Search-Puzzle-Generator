"""SQLite persistence for quality-approved word-search puzzles."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .generator import Placement, Puzzle, occurrences
from .parser import Topic, normalize
from .quality import QualityReport, evaluate

SCHEMA_VERSION = 1


def instructions_for(topic: str, count: int = 15) -> str:
    return (
        f"Find all {count} words related to {topic}. "
        "Words may appear horizontally, vertically, or diagonally, "
        "forwards or backwards. Words may intersect with one another."
    )


def _payload(puzzle: Puzzle) -> str:
    """Canonical identity includes topic, grid, and complete solution placements."""
    data = {
        "topic": puzzle.topic,
        "grid": puzzle.grid,
        "placements": [asdict(p) for p in puzzle.placements],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def puzzle_hash(puzzle: Puzzle) -> str:
    return hashlib.sha256(_payload(puzzle).encode("ascii")).hexdigest()


@contextmanager
def connect(path: str | Path) -> Iterator[sqlite3.Connection]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        _initialize(conn)
        yield conn
    finally:
        conn.close()


def _initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY,
            puzzle_hash TEXT NOT NULL UNIQUE,
            topic TEXT NOT NULL,
            grid_size INTEGER NOT NULL CHECK (grid_size >= 5),
            grid_json TEXT NOT NULL,
            topic_words_json TEXT NOT NULL,
            instructions TEXT NOT NULL,
            seed INTEGER NOT NULL,
            quality_score REAL NOT NULL CHECK (quality_score BETWEEN 0 AND 100),
            difficulty REAL NOT NULL CHECK (difficulty BETWEEN 0 AND 100),
            difficulty_category TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            puzzle_id INTEGER NOT NULL REFERENCES puzzles(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            original_word TEXT NOT NULL,
            normalized_word TEXT NOT NULL,
            start_row INTEGER NOT NULL,
            start_col INTEGER NOT NULL,
            dr INTEGER NOT NULL,
            dc INTEGER NOT NULL,
            end_row INTEGER NOT NULL,
            end_col INTEGER NOT NULL,
            UNIQUE (puzzle_id, position)
        );
        CREATE TABLE IF NOT EXISTS quality_metrics (
            puzzle_id INTEGER PRIMARY KEY REFERENCES puzzles(id) ON DELETE CASCADE,
            spatial_entropy REAL NOT NULL,
            direction_diversity REAL NOT NULL,
            spatial_coverage REAL NOT NULL,
            intersection_quality REAL NOT NULL,
            placement_balance REAL NOT NULL,
            metric_version TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_puzzles_topic ON puzzles(topic);
        """
    )
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, SCHEMA_VERSION):
        raise RuntimeError(f"Unsupported database schema version: {version}")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _validate(
    puzzle: Puzzle, topic: Topic, report: QualityReport, min_quality: float
) -> None:
    if not 0 <= min_quality <= 100:
        raise ValueError("Invalid minimum quality")
    if puzzle.topic != topic.name or len(puzzle.placements) != len(topic.words):
        raise ValueError("Puzzle and topic do not match")
    normalized = [normalize(word) for word in topic.words]
    if sorted(normalized) != sorted(p.word for p in puzzle.placements):
        raise ValueError("Puzzle words differ from topic input")
    if any(len(occurrences(puzzle.grid, word)) != 1 for word in normalized):
        raise ValueError("Target words must occur exactly once")
    actual = evaluate(puzzle)
    if actual != report:
        raise ValueError("Quality report does not match puzzle")
    if actual.score < min_quality:
        raise ValueError("Puzzle does not meet quality threshold")


def save_many(
    conn: sqlite3.Connection,
    items: list[tuple[Topic, Puzzle, QualityReport]],
    *,
    min_quality: float = 80,
) -> list[tuple[int, bool]]:
    """Atomically insert puzzles; return (id, newly_inserted) for each input."""
    for topic, puzzle, report in items:
        _validate(puzzle, topic, report, min_quality)
    result: list[tuple[int, bool]] = []
    with conn:
        for topic, puzzle, report in items:
            digest = puzzle_hash(puzzle)
            existing = conn.execute(
                "SELECT id FROM puzzles WHERE puzzle_hash = ?", (digest,)
            ).fetchone()
            if existing:
                result.append((existing[0], False))
                continue
            cursor = conn.execute(
                """INSERT INTO puzzles
                (puzzle_hash, topic, grid_size, grid_json, topic_words_json, instructions, seed,
                 quality_score, difficulty, difficulty_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    digest,
                    puzzle.topic,
                    len(puzzle.grid),
                    json.dumps(puzzle.grid),
                    json.dumps(topic.words),
                    instructions_for(topic.name, len(topic.words)),
                    puzzle.seed,
                    report.score,
                    report.difficulty,
                    report.difficulty_category,
                ),
            )
            puzzle_id = cursor.lastrowid
            original = {normalize(word): word for word in topic.words}
            for index, p in enumerate(puzzle.placements):
                end_row = p.row + (len(p.word) - 1) * p.dr
                end_col = p.col + (len(p.word) - 1) * p.dc
                conn.execute(
                    """INSERT INTO words
                    (puzzle_id, position, original_word, normalized_word,
                     start_row, start_col, dr, dc, end_row, end_col)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        puzzle_id,
                        index,
                        original[p.word],
                        p.word,
                        p.row,
                        p.col,
                        p.dr,
                        p.dc,
                        end_row,
                        end_col,
                    ),
                )
            conn.execute(
                """INSERT INTO quality_metrics
                (puzzle_id, spatial_entropy, direction_diversity, spatial_coverage,
                 intersection_quality, placement_balance, metric_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    puzzle_id,
                    report.spatial_entropy,
                    report.direction_diversity,
                    report.spatial_coverage,
                    report.intersection_quality,
                    report.placement_balance,
                    report.metric_version,
                ),
            )
            result.append((puzzle_id, True))
    return result


def load_puzzle(
    conn: sqlite3.Connection, puzzle_id: int
) -> tuple[Puzzle, Topic, QualityReport]:
    row = conn.execute(
        """SELECT topic, grid_json, topic_words_json, seed, quality_score, difficulty,
                  difficulty_category FROM puzzles WHERE id = ?""",
        (puzzle_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"Puzzle {puzzle_id} not found")
    topic_name, grid_json, topic_words_json, seed, score, difficulty, category = row
    word_rows = conn.execute(
        """SELECT original_word, normalized_word, start_row, start_col, dr, dc
           FROM words WHERE puzzle_id = ? ORDER BY position""",
        (puzzle_id,),
    ).fetchall()
    placements = tuple(Placement(w, r, c, dr, dc) for _, w, r, c, dr, dc in word_rows)
    topic = Topic(topic_name, tuple(json.loads(topic_words_json)))
    metrics = conn.execute(
        """SELECT spatial_entropy, direction_diversity, spatial_coverage,
                  intersection_quality, placement_balance, metric_version
           FROM quality_metrics WHERE puzzle_id = ?""",
        (puzzle_id,),
    ).fetchone()
    if metrics is None:
        raise ValueError(f"Missing quality metrics for puzzle {puzzle_id}")
    report = QualityReport(score, *metrics[:5], difficulty, category, metrics[5])
    puzzle = Puzzle(topic_name, tuple(json.loads(grid_json)), placements, seed)
    return puzzle, topic, report
