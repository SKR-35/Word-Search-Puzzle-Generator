"""SQLite round-trip, duplicate, and rejection tests."""

import pytest

from word_search_generator.database import connect, load_puzzle, save_many
from word_search_generator.generator import generate_quality
from word_search_generator.parser import parse_input


def sample():
    topic = parse_input("examples/input.txt")[0]
    puzzle, report = generate_quality(topic, candidates=8, min_quality=0)
    return topic, puzzle, report


def test_round_trip_and_deduplication(tmp_path):
    item = sample()
    with connect(tmp_path / "data" / "puzzles.db") as conn:
        assert save_many(conn, [item], min_quality=0) == [(1, True)]
        assert save_many(conn, [item], min_quality=0) == [(1, False)]
        assert load_puzzle(conn, 1) == (item[1], item[0], item[2])
        assert conn.execute("SELECT count(*) FROM words").fetchone()[0] == 15
        assert conn.execute("SELECT count(*) FROM quality_metrics").fetchone()[0] == 1


def test_rejects_below_threshold_without_writing(tmp_path):
    item = sample()
    with connect(tmp_path / "puzzles.db") as conn:
        with pytest.raises(ValueError, match="threshold"):
            save_many(conn, [item], min_quality=100)
        assert conn.execute("SELECT count(*) FROM puzzles").fetchone()[0] == 0


def test_batch_prevalidation_prevents_partial_save(tmp_path):
    topic, puzzle, report = sample()
    from word_search_generator.parser import Topic

    bad_topic = Topic("Wrong topic", topic.words)
    with connect(tmp_path / "puzzles.db") as conn:
        with pytest.raises(ValueError, match="do not match"):
            save_many(
                conn,
                [(topic, puzzle, report), (bad_topic, puzzle, report)],
                min_quality=0,
            )
        assert conn.execute("SELECT count(*) FROM puzzles").fetchone()[0] == 0


def test_missing_puzzle(tmp_path):
    with connect(tmp_path / "puzzles.db") as conn, pytest.raises(KeyError):
        load_puzzle(conn, 999)
