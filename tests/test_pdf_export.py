from pathlib import Path

import pytest

from word_search_generator.generator import generate_quality
from word_search_generator.parser import Topic
from word_search_generator.pdf_export import export_pdfs


def test_export_creates_two_pdf_files(tmp_path: Path):
    topic = Topic(
        "Greek Philosophy",
        (
            "SOCRATES",
            "PLATO",
            "ARISTOTLE",
            "LOGOS",
            "ETHICS",
            "VIRTUE",
            "REASON",
            "DIALECTIC",
            "ACADEMY",
            "STOICISM",
            "ATOMISM",
            "COSMOS",
            "SOPHIST",
            "EPISTEME",
            "METAPHYSICS",
        ),
    )
    puzzle, _ = generate_quality(topic, candidates=20, min_quality=0)
    files = export_pdfs([(1, puzzle, topic)] * 5, tmp_path)
    for path in files:
        assert path.exists()
        assert path.read_bytes().startswith(b"%PDF")
    from pypdf import PdfReader

    assert len(PdfReader(str(files[0])).pages) == 5
    assert len(PdfReader(str(files[1])).pages) == 2


def test_empty_export_rejected(tmp_path):
    with pytest.raises(ValueError):
        export_pdfs([], tmp_path)
