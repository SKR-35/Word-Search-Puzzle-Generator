import pytest

from word_search_generator.generator import generate, generate_quality
from word_search_generator.parser import parse_input
from word_search_generator.quality import WEIGHTS, evaluate


def topic():
    return parse_input("examples/input.txt")[0]


def test_quality_report_bounds_and_weights():
    assert sum(WEIGHTS.values()) == pytest.approx(1)
    report = evaluate(generate(topic(), seed=123))
    assert all(
        0 <= getattr(report, name) <= 100 for name in (*WEIGHTS, "score", "difficulty")
    )
    assert report.difficulty_category in ("Easy", "Medium", "Hard", "Expert")


def test_quality_determinism():
    a = generate_quality(topic(), seed=100, candidates=8, min_quality=0)
    b = generate_quality(topic(), seed=100, candidates=8, min_quality=0)
    assert a == b


def test_quality_gate_fails_closed():
    with pytest.raises(RuntimeError, match="Quality gate failed"):
        generate_quality(topic(), seed=100, candidates=1, min_quality=100)


def test_invalid_quality_arguments():
    with pytest.raises(ValueError):
        generate_quality(topic(), min_quality=101)
    with pytest.raises(ValueError):
        generate_quality(topic(), candidates=0)
