"""Deterministic eight-direction word search generation."""

import random
import string
from dataclasses import dataclass

from .parser import Topic, normalize

DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))


@dataclass(frozen=True)
class Placement:
    word: str
    row: int
    col: int
    dr: int
    dc: int


@dataclass(frozen=True)
class Puzzle:
    topic: str
    grid: tuple[str, ...]
    placements: tuple[Placement, ...]
    seed: int


def occurrences(grid: tuple[str, ...], word: str) -> list[tuple[int, int, int, int]]:
    n = len(grid)
    found = []
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRECTIONS:
                er, ec = r + (len(word) - 1) * dr, c + (len(word) - 1) * dc
                if not (0 <= er < n and 0 <= ec < n):
                    continue
                if all(grid[r + k * dr][c + k * dc] == ch for k, ch in enumerate(word)):
                    found.append((r, c, dr, dc))
    return found


def generate(
    topic: Topic, *, size: int = 20, seed: int = 42, attempts: int = 200
) -> Puzzle:
    """Generate a valid puzzle; quality acceptance is intentionally Phase 2."""
    if size < 5 or attempts < 1:
        raise ValueError("Invalid size or attempts")
    words = [normalize(w) for w in topic.words]
    if (
        len(words) != 15
        or len(set(words)) != 15
        or any(not w.isascii() or not w.isalpha() or len(w) > size for w in words)
    ):
        raise ValueError("Topic must contain 15 distinct A-Z words fitting the grid")
    rng = random.Random(seed)
    for _ in range(attempts):
        board = [[None for _ in range(size)] for _ in range(size)]
        placements: list[Placement] = []
        success = True
        for word in sorted(words, key=len, reverse=True):
            options = []
            for dr, dc in DIRECTIONS:
                for r in range(size):
                    for c in range(size):
                        er, ec = r + (len(word) - 1) * dr, c + (len(word) - 1) * dc
                        if not (0 <= er < size and 0 <= ec < size):
                            continue
                        if all(
                            board[r + k * dr][c + k * dc] in (None, ch)
                            for k, ch in enumerate(word)
                        ):
                            overlaps = sum(
                                board[r + k * dr][c + k * dc] == ch
                                for k, ch in enumerate(word)
                            )
                            options.append((r, c, dr, dc, overlaps))
            if not options:
                success = False
                break
            # Prefer intersections without forcing every word into one cluster.
            weights = [1 + min(item[4], 3) for item in options]
            r, c, dr, dc, _ = rng.choices(options, weights=weights, k=1)[0]
            for k, ch in enumerate(word):
                board[r + k * dr][c + k * dc] = ch
            placements.append(Placement(word, r, c, dr, dc))
        if not success:
            continue
        filled = tuple(
            "".join(
                ch if ch is not None else rng.choice(string.ascii_uppercase)
                for ch in row
            )
            for row in board
        )
        # Reject accidental extra appearances of any target word.
        if all(len(occurrences(filled, w)) == 1 for w in words):
            return Puzzle(topic.name, filled, tuple(placements), seed)
    raise RuntimeError(f"Could not place all words uniquely after {attempts} attempts")


def generate_quality(
    topic: Topic,
    *,
    size: int = 20,
    seed: int = 42,
    min_quality: float = 80,
    candidates: int = 100,
    attempts_per_candidate: int = 20,
):
    """Return highest-scoring valid candidate, or fail closed below threshold.

    Candidate seeds are deterministic and distinct; no low-quality fallback.
    """
    from .quality import evaluate

    if not 0 <= min_quality <= 100 or candidates < 1 or attempts_per_candidate < 1:
        raise ValueError("Invalid quality threshold or candidate count")

    best = None
    best_report = None

    for i in range(candidates):
        try:
            puzzle = generate(
                topic,
                size=size,
                seed=seed + i,
                attempts=attempts_per_candidate,
            )
        except RuntimeError:
            continue

        report = evaluate(puzzle)

        if best_report is None or report.score > best_report.score:
            best, best_report = puzzle, report

    if best is None or best_report.score < min_quality:
        best_score = best_report.score if best_report else None
        raise RuntimeError(
            f"Quality gate failed: best={best_score}, required={min_quality}; "
            f"tried {candidates} candidates"
        )

    return best, best_report
