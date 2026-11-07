"""Phase 1 preview CLI (does not persist or export)."""

import argparse

from .database import connect, load_puzzle, save_many
from .generator import generate_quality
from .parser import parse_input
from .pdf_export import export_pdfs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate word search previews")
    parser.add_argument("input", help="Text file containing one or more topic blocks")
    parser.add_argument("--size", type=int, default=20)
    parser.add_argument(
        "--words-per-topic",
        type=int,
        default=15,
        help="Required number of words per topic (default: 15)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-quality", type=float, default=80)
    parser.add_argument("--candidates", type=int, default=100)
    parser.add_argument(
        "--db",
        help="SQLite file path; omit for preview-only mode",
    )
    parser.add_argument(
        "--pdf-dir",
        help="Export puzzle and solution PDFs from saved records",
    )
    args = parser.parse_args()
    topics = parse_input(
        args.input, grid_size=args.size, words_per_topic=args.words_per_topic
    )
    generated = []
    for index, topic in enumerate(topics):
        puzzle, report = generate_quality(
            topic,
            size=args.size,
            seed=args.seed + index * 100000,
            min_quality=args.min_quality,
            candidates=args.candidates,
        )
        generated.append((topic, puzzle, report))

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

        if args.db:
            with connect(args.db) as conn:
                saved = save_many(
                    conn,
                    generated,
                    min_quality=args.min_quality,
                )

                pdf_items = (
                    [
                        (puzzle_id, *load_puzzle(conn, puzzle_id)[:2])
                        for puzzle_id, _ in saved
                    ]
                    if args.pdf_dir
                    else []
                )

            for (topic, _, _), (puzzle_id, inserted) in zip(generated, saved):
                status = "saved" if inserted else "already exists"
                print(f"{topic.name}: puzzle #{puzzle_id} ({status})")
            if args.pdf_dir:
                paths = export_pdfs(pdf_items, args.pdf_dir)
                print("PDF exports:", *paths, sep="\n  ")
        else:
            print("[PREVIEW ONLY: use --db to save; PDF is not implemented yet]")


if __name__ == "__main__":
    main()
