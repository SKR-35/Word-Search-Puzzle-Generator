"""Phase 1 preview CLI (does not persist or export)."""
import argparse
from .generator import generate
from .parser import parse_input


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate word search previews")
    parser.add_argument("input", help="Text file containing one or more topic blocks")
    parser.add_argument("--size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    topics = parse_input(args.input, grid_size=args.size)
    for index, topic in enumerate(topics):
        puzzle = generate(topic, size=args.size, seed=args.seed + index)
        print(f"\n{puzzle.topic} ({args.size}x{args.size})")
        print("\n".join(" ".join(row) for row in puzzle.grid))
        print("Words:", ", ".join(topic.words))
        print("[PREVIEW ONLY: quality filtering, SQLite and PDF are not implemented yet]")


if __name__ == "__main__":
    main()
