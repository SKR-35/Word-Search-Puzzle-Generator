"""Print-ready US Letter puzzle and four-up answer PDFs from saved puzzles."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = letter

# Print-friendly color palette
PRIMARY = HexColor("#35617D")
SECONDARY = HexColor("#A9C5D3")
TEXT = HexColor("#253746")
LIGHT = HexColor("#E8EFF3")


def _fit_title(
    c: canvas.Canvas, title: str, x: float, y: float, max_width: float, size: float
) -> None:
    while size > 10 and c.stringWidth(title, "Helvetica-Bold", size) > max_width:
        size -= 0.5
    if c.stringWidth(title, "Helvetica-Bold", size) > max_width:
        raise ValueError("Topic title is too long for the page")
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(TEXT)
    c.drawCentredString(x, y, title)


def _grid(
    c: canvas.Canvas,
    puzzle,
    *,
    x: float,
    top: float,
    width: float,
    answer: bool = False,
) -> None:
    n = len(puzzle.grid)
    if any(len(row) != n for row in puzzle.grid):
        raise ValueError("Non-square puzzle grid")
    step = width / n
    bottom = top - width
    c.setStrokeColor(HexColor("#ADB3B9"))
    c.setLineWidth(0.55 if not answer else 0.3)
    c.rect(x, bottom, width, width, stroke=1, fill=0)
    if answer:
        # Draw translucent highlights UNDER the letters; print-safe in grayscale too.
        c.saveState()
        c.setStrokeColor(PRIMARY)
        c.setLineCap(1)
        c.setLineWidth(step * 0.76)
        if hasattr(c, "setStrokeAlpha"):
            c.setStrokeAlpha(0.32)
        for p in puzzle.placements:
            x0 = x + (p.col + 0.5) * step
            y0 = top - (p.row + 0.5) * step
            x1 = x + (p.col + (len(p.word) - 1) * p.dc + 0.5) * step
            y1 = top - (p.row + (len(p.word) - 1) * p.dr + 0.5) * step
            c.line(x0, y0, x1, y1)
        c.restoreState()
    c.setFillColor(TEXT)
    font_size = min(step * 0.64, 15 if not answer else 8)
    c.setFont("Courier-Bold" if not answer else "Courier", font_size)
    for r, line in enumerate(puzzle.grid):
        for col, ch in enumerate(line):
            c.drawCentredString(
                x + (col + 0.5) * step, top - (r + 0.5) * step - font_size * 0.35, ch
            )


def export_pdfs(
    items: list[tuple[int, object, object]],
    output_dir: str | Path,
    *,
    prefix: str = "word-search",
) -> tuple[Path, Path]:
    """Export ordered (database_id, puzzle, topic) items; return two PDF paths."""
    if not items:
        raise ValueError("No puzzles selected for PDF export")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    puzzles_path = out / f"{prefix}-puzzles.pdf"
    solutions_path = out / f"{prefix}-solutions.pdf"
    c = canvas.Canvas(str(puzzles_path), pagesize=letter, pageCompression=1)
    c.setTitle("Word Search")
    for number, (_db_id, puzzle, topic) in enumerate(items, start=1):
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(PAGE_W / 2, 748, "WORD SEARCH")
        _fit_title(c, topic.name, PAGE_W / 2, 715, 510, 20)
        c.setFont("Helvetica", 9.5)
        c.setFillColor(TEXT)
        c.drawCentredString(
            PAGE_W / 2,
            690,
            f"PUZZLE {number:03d}  |  FIND ALL {len(topic.words)} WORDS",
        )
        c.setFont("Helvetica", 9)
        c.drawCentredString(
            PAGE_W / 2,
            670,
            "Search horizontally, vertically or diagonally; forwards or backwards.",
        )
        c.drawCentredString(PAGE_W / 2, 656, "Words may intersect with one another.")
        grid_width = 468
        _grid(c, puzzle, x=(PAGE_W - grid_width) / 2, top=632, width=grid_width)         

        # Word list: fit columns to the printable width and center the block.
        labels = [word.upper() for word in topic.words]
        available_width = 468
        column_gap = 14
        font_name = "Helvetica"

        layout = None

        # Prefer four columns for 20 words, three for 15 words.
        preferred_columns = 4 if len(labels) > 15 else 3

        for columns in range(preferred_columns, 1, -1):
            rows = (len(labels) + columns - 1) // columns

            # Keep the word list above the footer.
            if 128 - (rows - 1) * 13 < 52:
                continue

            for font_size in (10, 9.5, 9, 8.5, 8, 7.5, 7):
                groups = [
                    labels[col * rows : (col + 1) * rows]
                    for col in range(columns)
                ]
                widths = [
                    max(
                        (c.stringWidth(word, font_name, font_size)
                         for word in group),
                        default=0,
                    )
                    for group in groups
                ]
                total_width = sum(widths) + column_gap * (columns - 1)

                if total_width <= available_width:
                    layout = (groups, widths, font_size, total_width)
                    break

            if layout is not None:
                break

        if layout is None:
            raise ValueError(
                f"Word list cannot fit on the page: {topic.name}"
            )

        groups, widths, font_size, total_width = layout
        c.setStrokeColor(LIGHT)
        c.line(72, 146, 540, 146)
        c.setFont(font_name, font_size)
        c.setFillColor(TEXT)

        x = (PAGE_W - total_width) / 2
        for group, column_width in zip(groups, widths):
            for row, label in enumerate(group):
                c.drawString(x, 128 - row * 13, label)
            x += column_width + column_gap

        c.setFont("Helvetica", 8)
        c.setFillColor(PRIMARY)
        c.drawCentredString(PAGE_W / 2, 35, f"PUZZLES   |   {number}")
        c.showPage()
    c.save()

    s = canvas.Canvas(str(solutions_path), pagesize=letter, pageCompression=1)
    s.setTitle("Word Search Solutions")
    for base in range(0, len(items), 4):
        s.setFillColor(PRIMARY)
        s.setFont("Helvetica-Bold", 14)
        s.drawCentredString(PAGE_W / 2, 756, "SOLUTIONS")
        for local, (_db_id, puzzle, topic) in enumerate(items[base : base + 4]):
            col, row = local % 2, local // 2
            center_x = 164 if col == 0 else 448
            top = 714 if row == 0 else 358
            s.setFillColor(TEXT)
            s.setFont("Helvetica-Bold", 10)
            s.drawCentredString(center_x, top, f"PUZZLE {base + local + 1:03d}")
            _fit_title(s, topic.name, center_x, top - 16, 258, 9)
            _grid(s, puzzle, x=center_x - 125, top=top - 27, width=250, answer=True)
        s.showPage()
    s.save()
    return puzzles_path, solutions_path
