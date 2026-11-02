"""Parse topic blocks and validate puzzle vocabulary."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Topic:
    name: str
    words: tuple[str, ...]


def normalize(word: str) -> str:
    return re.sub(r"[ -]", "", word.upper())


def parse_input(path: str | Path, *, grid_size: int = 20) -> list[Topic]:
    if grid_size < 5:
        raise ValueError("Grid size must be at least 5")
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    topics: list[Topic] = []
    current_name: str | None = None
    current_words: list[str] = []

    def finish() -> None:
        if current_name is None:
            return
        if len(current_words) != 15:
            raise ValueError(
                f"Topic '{current_name}' requires exactly 15 words; got {len(current_words)}"
            )
        normalized = [normalize(w) for w in current_words]
        if len(set(normalized)) != 15:
            raise ValueError(f"Duplicate words in topic '{current_name}'")
        topics.append(Topic(current_name, tuple(current_words)))

    for line_no, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("topic:"):
            finish()
            current_name = line.split(":", 1)[1].strip()
            if not current_name:
                raise ValueError(f"Empty topic on line {line_no}")
            current_words = []
            continue
        if current_name is None:
            raise ValueError(f"Word before topic declaration on line {line_no}")
        if not re.fullmatch(r"[A-Za-z]+(?:[ -][A-Za-z]+)*", line):
            raise ValueError(f"Invalid word/phrase on line {line_no}: {line!r}")
        word = normalize(line)
        if len(word) > grid_size:
            raise ValueError(f"Word {line!r} exceeds grid size {grid_size}")
        if len(word) < 2:
            raise ValueError(f"Word {line!r} is too short")
        current_words.append(line.upper())
    finish()
    if not topics:
        raise ValueError("No topics found")
    return topics
