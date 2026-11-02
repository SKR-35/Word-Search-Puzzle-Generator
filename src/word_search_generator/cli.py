"""Phase 1 preview CLI (does not persist or export)."""

import argparse

from .generator import generate_quality
from .parser import parse_input


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate word search previews")
    parser.add_argument("input", help="Text file containing one or more topic blocks")
    parser.add_argument("--size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-quality", type=float, default=80)
    parser.add_argument("--candidates", type=int, default=100)
    args = parser.parse_args()
    topics = parse_input(args.input, grid_size=args.size)
    for index, topic in enumerate(topics):
        puzzle, report = generate_quality(
            topic,
            size=args.size,
            seed=args.seed + index * 100000,
            min_quality=args.min_quality,
            candidates=args.candidates,
        )
        print(f"\n{puzzle.topic} ({args.size}x{args.size})")
        print("\n".join(" ".join(row) for row in puzzle.grid))
        print("Words:", ", ".join(topic.words))

        print(
            f"Quality: {report.score}/100 (threshold {args.min_quality}) | "
            f"Difficulty: {report.difficulty}/100 ({report.difficulty_category})"
        )

        print(
            f"Metrics: entropy={report.spatial_entropy}, "
            f"directions={report.direction_diversity}, "
            f"coverage={report.spatial_coverage}, "
            f"intersections={report.intersection_quality}, "
            f"balance={report.placement_balance}"
        )

        print("[PREVIEW ONLY: SQLite and PDF are not implemented yet]")


if __name__ == "__main__":
    main()
