"""
modules/pdf_builder.py — Professional, watermark-free PDF generation via ReportLab.

Renders a polished, multi-section resume PDF from Markdown text.
Handles:
  - Contact header block with styled name
  - Section headings with decorative horizontal rules
  - Bullet point indentation
  - Automatic page overflow / multi-page support
  - Consistent font hierarchy and spacing
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    KeepTogether, ListFlowable, ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#   Color Palette
# ─────────────────────────────────────────────
COLOR_NAME    = colors.HexColor("#1a1a2e")   # Deep navy for name
COLOR_HEADING = colors.HexColor("#16213e")   # Section headings
COLOR_RULE    = colors.HexColor("#4a90d9")   # Accent blue rule
COLOR_BODY    = colors.HexColor("#2d2d2d")   # Body text
COLOR_META    = colors.HexColor("#555555")   # Contact / meta info
COLOR_BULLET  = colors.HexColor("#4a90d9")   # Bullet accent

# ─────────────────────────────────────────────
#   Style Definitions
# ─────────────────────────────────────────────
def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {
        "name": ParagraphStyle(
            "ResumeName",
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=COLOR_NAME,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "contact": ParagraphStyle(
            "ResumeContact",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=COLOR_META,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=COLOR_HEADING,
            spaceBefore=10,
            spaceAfter=2,
        ),
        "job_title": ParagraphStyle(
            "JobTitle",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=COLOR_BODY,
            spaceBefore=6,
            spaceAfter=1,
        ),
        "body": ParagraphStyle(
            "ResumeBody",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=COLOR_BODY,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "ResumeBullet",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=COLOR_BODY,
            leftIndent=14,
            spaceAfter=2,
            bulletIndent=4,
            bulletFontName="Helvetica",
            bulletFontSize=10,
            bulletColor=COLOR_BULLET,
        ),
    }
    return styles


# ─────────────────────────────────────────────
#   Markdown → ReportLab Flowables Parser
# ─────────────────────────────────────────────
def _inline_md(text: str) -> str:
    """Convert basic inline Markdown (**bold**, *italic*) to ReportLab XML tags."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    # Escape bare ampersands that aren't part of XML entities
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;)", "&amp;", text)
    return text


def _parse_markdown_to_flowables(md_text: str, styles: dict) -> list:
    """
    Parses a Markdown resume into a list of ReportLab Flowables.

    Recognized patterns (in order of priority):
      # Name line         → name style (first H1 only)
      ## Section Header   → section heading + rule
      ### Job Title line  → job title style
      - Bullet item       → bullet list item
      ---                 → spacer (horizontal divider absorbed into section rules)
      blank line          → small vertical spacer
      plain text          → body paragraph
    """
    flowables = []
    styles_map = styles
    lines = md_text.split("\n")
    first_h1_seen = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # ── H1: Candidate name ──────────────────────────────
        if line.startswith("# ") and not first_h1_seen:
            name = line[2:].strip()
            flowables.append(Paragraph(_inline_md(name), styles_map["name"]))
            first_h1_seen = True

        # ── H2: Section heading ──────────────────────────────
        elif line.startswith("## "):
            heading_text = line[3:].strip().upper()
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(_inline_md(heading_text), styles_map["section_heading"]))
            flowables.append(HRFlowable(
                width="100%", thickness=1.2,
                color=COLOR_RULE, spaceAfter=4
            ))

        # ── H3: Sub-heading / Job title ───────────────────────
        elif line.startswith("### "):
            flowables.append(Paragraph(_inline_md(line[4:].strip()), styles_map["job_title"]))

        # ── Horizontal rule (---) — skip, handled by section logic ──
        elif re.match(r"^-{3,}$", line):
            pass  # Separator absorbed into section heading rule

        # ── Bullet items ─────────────────────────────────────
        elif line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            flowables.append(Paragraph(
                f"• {_inline_md(bullet_text)}",
                styles_map["bullet"]
            ))

        # ── Contact / meta line (contains | separators) ───────
        elif "|" in line and not line.startswith("#"):
            flowables.append(Paragraph(_inline_md(line.strip()), styles_map["contact"]))

        # ── Blank line ────────────────────────────────────────
        elif line.strip() == "":
            flowables.append(Spacer(1, 3))

        # ── Plain body text ───────────────────────────────────
        else:
            flowables.append(Paragraph(_inline_md(line.strip()), styles_map["body"]))

        i += 1

    return flowables


# ─────────────────────────────────────────────
#   Public API
# ─────────────────────────────────────────────
def build_pdf(tailored_text: str, job_data: dict, dry_run: bool = False) -> str:
    """
    Compiles a professional, watermark-free PDF resume from the tailored Markdown text.

    Args:
        tailored_text: Tailored resume in Markdown format
        job_data: Dict with keys: title, company
        dry_run: If True, writes a placeholder PDF

    Returns:
        Absolute path to the saved PDF file as a string
    """
    safe_company = re.sub(r"[^\w]", "", job_data["company"])[:30]
    safe_title   = re.sub(r"[^\w]", "", job_data["title"])[:30]
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename     = f"Resume_{safe_company}_{safe_title}_{timestamp}.pdf"
    output_path  = config.OUTPUT_DIR / filename

    logger.info(f"Building PDF: {output_path}")

    if dry_run:
        output_path.write_text(f"[DRY RUN PDF] {filename}\n{tailored_text}")
        logger.info(f"[DRY RUN] Wrote placeholder: {output_path}")
        return str(output_path)

    styles = _build_styles()
    flowables = _parse_markdown_to_flowables(tailored_text, styles)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{job_data['title']} Resume — {job_data['company']}",
        author="Auto Applier",
        creator="Auto Applier (ReportLab)",
    )

    doc.build(flowables)
    logger.info(f"PDF saved: {output_path}")
    return str(output_path)
