"""Versioned, interpretable placement-quality and difficulty heuristics."""

import math
from collections import Counter
from dataclasses import dataclass

from .generator import DIRECTIONS, Puzzle

METRIC_VERSION = "1.0"
WEIGHTS = {
    "spatial_entropy": 0.35,
    "direction_diversity": 0.25,
    "spatial_coverage": 0.20,
    "intersection_quality": 0.10,
    "placement_balance": 0.10,
}


@dataclass(frozen=True)
class QualityReport:
    score: float
    spatial_entropy: float
    direction_diversity: float
    spatial_coverage: float
    intersection_quality: float
    placement_balance: float
    difficulty: float
    difficulty_category: str
    metric_version: str = METRIC_VERSION


def evaluate(puzzle: Puzzle) -> QualityReport:
    """Score word placements, not random filler; all components are in [0, 100]."""
    n = len(puzzle.grid)
    if n < 5 or any(len(row) != n for row in puzzle.grid) or not puzzle.placements:
        raise ValueError("Invalid square puzzle")
    cell_uses: Counter[tuple[int, int]] = Counter()
    region_uses: Counter[tuple[int, int]] = Counter()
    directions: Counter[tuple[int, int]] = Counter()
    starts: list[tuple[float, float]] = []
    total = 0
    for p in puzzle.placements:
        if (p.dr, p.dc) not in DIRECTIONS:
            raise ValueError("Invalid direction")
        directions[p.dr, p.dc] += 1
        coords = [(p.row + k * p.dr, p.col + k * p.dc) for k in range(len(p.word))]
        if any(
            not (0 <= r < n and 0 <= c < n) or puzzle.grid[r][c] != p.word[k]
            for k, (r, c) in enumerate(coords)
        ):
            raise ValueError("Invalid placement")
        for r, c in coords:
            cell_uses[r, c] += 1
            region_uses[min(3, 4 * r // n), min(3, 4 * c // n)] += 1
            total += 1
        starts.append(
            (
                (coords[0][0] + coords[-1][0]) / 2 / n,
                (coords[0][1] + coords[-1][1]) / 2 / n,
            )
        )
    probs = [v / total for v in region_uses.values()]
    entropy = -sum(p * math.log(p) for p in probs) / math.log(16) * 100
    direction_probs = [v / len(puzzle.placements) for v in directions.values()]
    direction_score = -sum(p * math.log(p) for p in direction_probs) / math.log(8) * 100
    # Coverage measures occupied regions, not how much random filler is present.
    coverage = len(region_uses) / 16 * 100
    overlaps = sum(v - 1 for v in cell_uses.values() if v > 1)
    # Reward moderate, not excessive intersections; 1 overlap per ~12 letters is ideal.
    intersection = max(0.0, 100 * (1 - abs(overlaps / total - 1 / 12) / (1 / 12)))
    # Word-midpoint balance penalizes strong left/right or top/bottom clustering.
    mean_r = sum(r for r, _ in starts) / len(starts)
    mean_c = sum(c for _, c in starts) / len(starts)
    balance = max(
        0.0, 100 * (1 - 2 * math.hypot(mean_r - 0.5, mean_c - 0.5) / math.sqrt(0.5))
    )
    components = {
        "spatial_entropy": entropy,
        "direction_diversity": direction_score,
        "spatial_coverage": coverage,
        "intersection_quality": intersection,
        "placement_balance": balance,
    }
    score = sum(WEIGHTS[k] * v for k, v in components.items())
    reverse = sum(
        (p.dr, p.dc) in ((0, -1), (-1, 0), (-1, -1), (-1, 1)) for p in puzzle.placements
    )
    diagonal = sum(p.dr != 0 and p.dc != 0 for p in puzzle.placements)
    avg_length = total / len(puzzle.placements)
    difficulty = max(
        0.0,
        min(
            100.0,
            20
            + 30 * reverse / len(puzzle.placements)
            + 25 * diagonal / len(puzzle.placements)
            + 15 * min(avg_length / n, 1)
            + 10 * min(overlaps / len(puzzle.placements), 1),
        ),
    )
    category = (
        "Easy"
        if difficulty < 25
        else "Medium"
        if difficulty < 50
        else "Hard"
        if difficulty < 75
        else "Expert"
    )
    return QualityReport(
        round(score, 2),
        *(round(components[k], 2) for k in WEIGHTS),
        round(difficulty, 2),
        category,
    )
