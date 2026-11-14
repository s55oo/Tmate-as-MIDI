#!/usr/bin/env python3
"""Build the TMate 1.0 Windows manual PDF from docs/windows.md."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SOURCE = REPO / "docs" / "windows.md"
OUTPUT = REPO / "TMate-1.0-Windows-Manual.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans-Oblique", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans-BoldOblique", str(FONT_DIR / "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSansMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSansMono-Bold", str(FONT_DIR / "DejaVuSansMono-Bold.ttf")))
pdfmetrics.registerFontFamily(
    "DejaVuSans",
    normal="DejaVuSans",
    bold="DejaVuSans-Bold",
    italic="DejaVuSans-Oblique",
    boldItalic="DejaVuSans-BoldOblique",
)

INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#64748b")
NAVY = colors.HexColor("#0f1b2d")
NAVY_2 = colors.HexColor("#15263d")
BLUE = colors.HexColor("#1d4ed8")
GOLD = colors.HexColor("#d97706")
GOLD_LIGHT = colors.HexColor("#f6c56b")
LINE = colors.HexColor("#d8dee9")
WHITE = colors.white
CODE_BG = colors.HexColor("#f6f8fa")
CODE_BORDER = colors.HexColor("#d0d7de")
CALLOUT_BG = colors.HexColor("#fff7e6")

PAGE_W, PAGE_H = A4
LEFT = 19 * mm
RIGHT = 19 * mm
TOP = 25 * mm
BOTTOM = 18 * mm
CONTENT_W = PAGE_W - LEFT - RIGHT

body_style = ParagraphStyle(
    "Body",
    fontName="DejaVuSans",
    fontSize=9.4,
    leading=13.2,
    textColor=INK,
    spaceAfter=5,
    alignment=TA_LEFT,
    splitLongWords=1,
    allowWidows=0,
    allowOrphans=0,
)
bullet_style = ParagraphStyle(
    "Bullet",
    parent=body_style,
    leftIndent=14,
    bulletIndent=2,
    spaceAfter=3,
)
h1_style = ParagraphStyle(
    "H1",
    fontName="DejaVuSans-Bold",
    fontSize=21,
    leading=25,
    textColor=NAVY,
    spaceBefore=0,
    spaceAfter=10,
)
h2_style = ParagraphStyle(
    "H2",
    fontName="DejaVuSans-Bold",
    fontSize=15,
    leading=19,
    textColor=NAVY,
    spaceBefore=15,
    spaceAfter=4,
    keepWithNext=1,
)
h3_style = ParagraphStyle(
    "H3",
    fontName="DejaVuSans-Bold",
    fontSize=11,
    leading=14,
    textColor=BLUE,
    spaceBefore=11,
    spaceAfter=2,
    keepWithNext=1,
)
h4_style = ParagraphStyle(
    "H4",
    fontName="DejaVuSans-Bold",
    fontSize=9.8,
    leading=12.5,
    textColor=INK,
    spaceBefore=8,
    spaceAfter=2,
    keepWithNext=1,
)
code_style = ParagraphStyle(
    "Code",
    fontName="DejaVuSansMono",
    fontSize=7.6,
    leading=9.5,
    textColor=INK,
    spaceAfter=0,
)
cell_style = ParagraphStyle(
    "Cell",
    fontName="DejaVuSans",
    fontSize=8.1,
    leading=10.4,
    textColor=INK,
    spaceAfter=0,
    splitLongWords=1,
)
cell_head_style = ParagraphStyle(
    "CellHead",
    parent=cell_style,
    fontName="DejaVuSans-Bold",
    textColor=WHITE,
)
callout_style = ParagraphStyle(
    "Callout",
    parent=body_style,
    fontSize=9,
    leading=12.5,
    spaceAfter=0,
)
toc_styles = [
    ParagraphStyle(
        "TOC0",
        fontName="DejaVuSans-Bold",
        fontSize=10.6,
        leading=16,
        textColor=NAVY,
        spaceBefore=5,
    ),
    ParagraphStyle(
        "TOC1",
        fontName="DejaVuSans",
        fontSize=9,
        leading=13,
        leftIndent=14,
        textColor=INK,
    ),
]


def slugify(text: str) -> str:
    text = re.sub(r"[`*_]", "", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def inline(text: str) -> str:
    """Convert the tiny Markdown subset used by the manual to ReportLab XML."""
    parts = text.split("`")
    out = []
    for index, part in enumerate(parts):
        if index % 2 == 1:
            out.append(
                '<font name="DejaVuSansMono" size="8.4" color="#8a2c0d">'
                + html.escape(part, quote=False)
                + "</font>"
            )
            continue
        segment = html.escape(part, quote=False)
        segment = re.sub(
            r"&lt;(https?://[^&]+?)&gt;",
            lambda m: (
                f'<link href="{m.group(1)}" color="#1d4ed8">'
                f"{m.group(1)}</link>"
            ),
            segment,
        )
        segment = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            lambda m: (
                f'<link href="{m.group(2)}" color="#1d4ed8">'
                f"{m.group(1)}</link>"
            ),
            segment,
        )
        segment = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", segment)
        segment = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", segment)
        out.append(segment)
    return "".join(out)


def plain_text(text: str) -> str:
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"&lt;.*?&gt;", "", text)
    return text


def make_code_block(lines: list[str]) -> Table:
    max_len = max((len(line) for line in lines), default=0)
    size = 7.6 if max_len <= 106 else 7.1 if max_len <= 114 else 6.6
    style = ParagraphStyle(
        "CodeBlock",
        parent=code_style,
        fontSize=size,
        leading=size * 1.26,
    )
    block = Preformatted("\n".join(lines), style)
    table = Table([[block]], colWidths=[CONTENT_W])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, CODE_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def make_callout(text: str) -> Table:
    content = Paragraph(
        "<b>Important:</b> " + inline(text),
        callout_style,
    )
    table = Table([[content]], colWidths=[CONTENT_W])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CALLOUT_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def parse_table(lines: list[str]) -> Table:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip().strip("|")
        cells = [cell.strip() for cell in stripped.split("|")]
        rows.append(cells)
    separator = rows[1] if len(rows) > 1 else []
    is_separator = separator and all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    )
    if is_separator:
        header = rows[0]
        data_rows = rows[2:]
    else:
        header = rows[0]
        data_rows = rows[1:]
    columns = max(len(row) for row in rows)
    header = header + [""] * (columns - len(header))
    data_rows = [row + [""] * (columns - len(row)) for row in data_rows]
    data = [
        [Paragraph(inline(cell), cell_head_style) for cell in header]
    ] + [
        [Paragraph(inline(cell), cell_style) for cell in row]
        for row in data_rows
    ]
    col_widths = [CONTENT_W / columns] * columns
    table = Table(data, colWidths=col_widths, repeatRows=1, splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [WHITE, colors.HexColor("#f6f8fb")],
                ),
            ]
        )
    )
    return table


def build_story(markdown: str, entries: list) -> tuple[list, TableOfContents]:
    lines = markdown.splitlines()
    story: list = [Spacer(1, 1), NextPageTemplate("body"), PageBreak()]
    toc = TableOfContents()
    toc.levelStyles = toc_styles
    toc.dotsMinLevel = 0
    toc.addEntries(entries)
    toc.beforeBuild()
    story.append(Paragraph("Contents", h1_style))
    story.append(Spacer(1, 4))
    story.append(toc)
    story.append(PageBreak())

    anchors: set[str] = set()
    paragraph: list[str] = []
    bullets: list[str] = []
    callout: list[str] = []
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), body_style))
            paragraph = []

    def flush_bullets() -> None:
        nonlocal bullets
        for item in bullets:
            story.append(Paragraph(inline(item), bullet_style, bulletText="•"))
        if bullets:
            story.append(Spacer(1, 3))
        bullets = []

    def flush_callout() -> None:
        nonlocal callout
        if callout:
            story.append(Spacer(1, 4))
            story.append(make_callout(" ".join(callout)))
            story.append(Spacer(1, 6))
            callout = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_bullets()
            flush_callout()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            spacer = Spacer(1, 4)
            spacer.keepWithNext = 1
            story.append(spacer)
            story.append(make_code_block(code_lines))
            story.append(Spacer(1, 6))
            continue

        if stripped.startswith("|"):
            flush_paragraph()
            flush_bullets()
            flush_callout()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            spacer = Spacer(1, 4)
            spacer.keepWithNext = 1
            story.append(spacer)
            story.append(parse_table(table_lines))
            story.append(Spacer(1, 7))
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_bullets()
            callout.append(stripped.lstrip(">").strip())
            i += 1
            continue

        match = re.match(r"^(#{2,4})\s+(.*)$", stripped)
        if match:
            flush_paragraph()
            flush_bullets()
            flush_callout()
            level = len(match.group(1))
            text = match.group(2).strip()
            slug = slugify(plain_text(text))
            base = slug
            counter = 2
            while slug in anchors:
                slug = f"{base}-{counter}"
                counter += 1
            anchors.add(slug)
            style = h2_style if level == 2 else h3_style if level == 3 else h4_style
            heading = Paragraph(f'<a name="{slug}"/>{inline(text)}', style)
            heading._toc_key = f"toc-{slug}"
            story.append(heading)
            if level == 2:
                rule = HRFlowable(
                    width="100%",
                    thickness=0.7,
                    color=GOLD,
                    spaceBefore=1,
                    spaceAfter=7,
                )
                rule.keepWithNext = 1
                story.append(rule)
            i += 1
            continue

        if stripped in ("---", "***"):
            flush_paragraph()
            flush_bullets()
            flush_callout()
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=LINE,
                    spaceBefore=8,
                    spaceAfter=8,
                )
            )
            i += 1
            continue

        bullet_match = re.match(r"^\s*[-*]\s+(.*)$", line)
        if bullet_match:
            flush_paragraph()
            flush_callout()
            item = bullet_match.group(1).strip()
            i += 1
            while i < len(lines):
                continuation = lines[i]
                if continuation.startswith("  ") and continuation.strip():
                    item += " " + continuation.strip()
                    i += 1
                else:
                    break
            bullets.append(item)
            continue

        number_match = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if number_match:
            flush_paragraph()
            flush_callout()
            item = number_match.group(2).strip()
            i += 1
            while i < len(lines):
                continuation = lines[i]
                if continuation.startswith("  ") and continuation.strip():
                    item += " " + continuation.strip()
                    i += 1
                else:
                    break
            story.append(
                Paragraph(
                    inline(item),
                    bullet_style,
                    bulletText=number_match.group(1) + ".",
                )
            )
            continue

        if not stripped:
            flush_paragraph()
            flush_bullets()
            flush_callout()
            i += 1
            continue

        if callout:
            callout.append(stripped)
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    flush_bullets()
    flush_callout()
    return story, toc


class ManualDoc(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        cover_frame = Frame(
            LEFT,
            BOTTOM,
            CONTENT_W,
            PAGE_H - TOP - BOTTOM,
            id="cover-frame",
            showBoundary=0,
        )
        body_frame = Frame(
            LEFT,
            BOTTOM,
            CONTENT_W,
            PAGE_H - TOP - BOTTOM,
            id="body-frame",
            showBoundary=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[cover_frame], onPage=self.draw_cover),
                PageTemplate(id="body", frames=[body_frame], onPage=self.draw_body),
            ]
        )

    def draw_cover(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        canvas.setFillColor(NAVY_2)
        canvas.rect(0, 0, PAGE_W, PAGE_H * 0.72, stroke=0, fill=1)

        canvas.setFillColor(GOLD)
        canvas.rect(22 * mm, PAGE_H - 27 * mm, 40 * mm, 2.1 * mm, stroke=0, fill=1)

        cx, cy, radius = PAGE_W - 76 * mm, PAGE_H - 95 * mm, 36 * mm
        canvas.setStrokeColor(colors.HexColor("#2b3f5c"))
        canvas.setLineWidth(10)
        canvas.circle(cx, cy, radius + 7 * mm, stroke=1, fill=0)
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(2.2)
        canvas.circle(cx, cy, radius, stroke=1, fill=0)
        canvas.setFillColor(colors.HexColor("#0a1422"))
        canvas.circle(cx, cy, radius - 6 * mm, stroke=0, fill=1)
        for tick in range(24):
            import math

            angle = math.radians(tick * 15)
            inner = radius - 10 * mm
            outer = radius - 3 * mm
            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer
            canvas.setStrokeColor(
                GOLD_LIGHT if tick % 6 == 0 else colors.HexColor("#4a5f7d")
            )
            canvas.setLineWidth(2.0 if tick % 6 == 0 else 1.0)
            canvas.line(x1, y1, x2, y2)
        canvas.setFillColor(colors.HexColor("#20344f"))
        canvas.circle(cx, cy, 14 * mm, stroke=0, fill=1)
        canvas.setFillColor(GOLD_LIGHT)
        canvas.circle(cx, cy, 3.2 * mm, stroke=0, fill=1)
        canvas.setStrokeColor(GOLD_LIGHT)
        canvas.setLineWidth(3)
        canvas.line(cx, cy, cx, cy + 13 * mm)
        canvas.setFillColor(GOLD)
        canvas.circle(cx, cy + 13 * mm, 2.2 * mm, stroke=0, fill=1)

        for index in range(4):
            x = cx - 20 * mm + index * 10 * mm
            y = cy - radius - 15 * mm
            canvas.setFillColor(colors.HexColor("#20344f"))
            canvas.roundRect(
                x - 3.2 * mm,
                y - 3.2 * mm,
                6.4 * mm,
                6.4 * mm,
                1.5 * mm,
                stroke=0,
                fill=1,
            )
            canvas.setFillColor(GOLD if index == 0 else colors.HexColor("#6b7f99"))
            canvas.circle(x, y, 1.2 * mm, stroke=0, fill=1)

        canvas.setFillColor(WHITE)
        canvas.setFont("DejaVuSans-Bold", 42)
        canvas.drawString(22 * mm, PAGE_H - 62 * mm, "TMate 1.0")
        canvas.setFillColor(colors.HexColor("#dbe4ef"))
        canvas.setFont("DejaVuSans", 17)
        canvas.drawString(
            22 * mm, PAGE_H - 76 * mm, "Windows Setup & MIDI Controller Manual"
        )
        canvas.setFillColor(GOLD_LIGHT)
        canvas.setFont("DejaVuSans-Bold", 9)
        canvas.drawString(
            22 * mm,
            PAGE_H - 86 * mm,
            "WINDOWS 10 / 11  ·  64-BIT  ·  VERSION 0.1.0",
        )

        canvas.setStrokeColor(colors.HexColor("#2b3f5c"))
        canvas.setLineWidth(0.8)
        canvas.line(22 * mm, PAGE_H - 96 * mm, PAGE_W - 22 * mm, PAGE_H - 96 * mm)

        canvas.setFillColor(colors.HexColor("#c9d5e4"))
        canvas.setFont("DejaVuSans", 10.5)
        text_lines = [
            "Wheel to relative MIDI CC. Four keys to notes or CCs.",
            "WinUSB with Zadig, loopMIDI routing, local web configurator,",
            "DAW mapping, autostart and troubleshooting.",
        ]
        y = PAGE_H - 112 * mm
        for text in text_lines:
            canvas.drawString(22 * mm, y, text)
            y -= 6.2 * mm

        canvas.setFillColor(GOLD)
        canvas.setFont("DejaVuSans-Bold", 9.5)
        canvas.drawString(
            22 * mm,
            38 * mm,
            "Read this manual before installing the USB driver.",
        )
        canvas.setFillColor(colors.HexColor("#8fa4bd"))
        canvas.setFont("DejaVuSans", 8)
        canvas.drawString(
            22 * mm,
            31 * mm,
            "Includes driver setup, MIDI routing, configurator reference and troubleshooting.",
        )
        canvas.setFillColor(colors.HexColor("#5f7692"))
        canvas.setFont("DejaVuSans", 7.5)
        canvas.drawString(22 * mm, 18 * mm, "TMate-1.0-Windows-Manual.pdf")
        canvas.drawRightString(
            PAGE_W - 22 * mm, 18 * mm, "November 2026"
        )
        canvas.restoreState()

    def draw_body(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, PAGE_H - 18 * mm, PAGE_W - RIGHT, PAGE_H - 18 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("DejaVuSans", 7.4)
        canvas.drawString(
            LEFT,
            PAGE_H - 15.5 * mm,
            "TMate 1.0  ·  Windows Setup & MIDI Controller Manual",
        )
        canvas.drawRightString(PAGE_W - RIGHT, PAGE_H - 15.5 * mm, "v0.1.0")
        canvas.line(LEFT, 14 * mm, PAGE_W - RIGHT, 14 * mm)
        canvas.setFont("DejaVuSans", 8)
        canvas.drawString(LEFT, 9.5 * mm, "TMate 1.0  ·  Windows")
        canvas.drawRightString(
            PAGE_W - RIGHT, 9.5 * mm, f"Page {canvas.getPageNumber()}"
        )
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        name = flowable.style.name
        if name not in ("H2", "H3"):
            return
        level = 0 if name == "H2" else 1
        text = flowable.getPlainText()
        key = getattr(flowable, "_toc_key", None)
        if not key:
            return
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


def main() -> int:
    markdown = SOURCE.read_text(encoding="utf-8")
    entries: list = []
    for attempt in range(1, 11):
        story, toc = build_story(markdown, entries)
        temp = OUTPUT.with_name(f"{OUTPUT.stem}.pass{attempt}.pdf")
        doc = ManualDoc(
            str(temp),
            pagesize=A4,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="TMate 1.0 - Windows Setup & MIDI Controller Manual",
            author="TMate 1.0 project",
            subject="Windows 10/11 setup, WinUSB, loopMIDI, MIDI mapping, troubleshooting",
            creator="TMate 1.0 manual builder",
        )
        doc._indexingFlowables = [toc]
        doc.build(story)
        toc.afterBuild()
        new_entries = list(toc._entries)
        if new_entries == entries:
            temp.replace(OUTPUT)
            for stale in OUTPUT.parent.glob(f"{OUTPUT.stem}.pass*.pdf"):
                stale.unlink()
            print(
                f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes) "
                f"after {attempt} layout pass(es)"
            )
            return 0
        entries = new_entries
        print(f"layout pass {attempt}: TOC moved, rebuilding")
    raise RuntimeError("table of contents did not settle")


if __name__ == "__main__":
    sys.exit(main())
