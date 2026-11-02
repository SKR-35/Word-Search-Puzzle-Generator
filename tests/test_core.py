import pytest

from word_search_generator.generator import generate, occurrences
from word_search_generator.parser import parse_input


def test_multiple_topics():
    topics = parse_input("examples/input.txt")
    assert len(topics) == 2
    assert all(len(t.words) == 15 for t in topics)


@pytest.mark.parametrize("size", [15, 20, 25])
def test_generation_and_uniqueness(size):
    topic = parse_input("examples/input.txt", grid_size=size)[0]
    puzzle = generate(topic, size=size, seed=123)
    assert len(puzzle.grid) == size
    assert all(len(row) == size for row in puzzle.grid)
    assert len(puzzle.placements) == 15
    assert all(len(occurrences(puzzle.grid, p.word)) == 1 for p in puzzle.placements)
    assert generate(topic, size=size, seed=123) == puzzle


def test_bad_input(tmp_path):
    p = tmp_path / "input.txt"
    p.write_text("topic: Bad\nALPHA\n")
    with pytest.raises(ValueError, match="exactly 15"):
        parse_input(p)
