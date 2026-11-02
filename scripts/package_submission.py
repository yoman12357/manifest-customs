"""Build the required two-file submission; source stays in the public repository."""

import re
import zipfile
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    PageBreak,
    Image,
)

ROOT = Path(__file__).resolve().parents[1]


def build():
    dest = ROOT / "submission"
    dest.mkdir(exist_ok=True)
    pdf = dest / "Manifest_TDD.pdf"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ManifestTitle",
            fontName="Helvetica-Bold",
            fontSize=30,
            leading=35,
            textColor=colors.HexColor("#204e40"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=21,
            textColor=colors.HexColor("#204e40"),
            spaceBefore=18,
            spaceAfter=12,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Copy",
            fontName="Helvetica",
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#405048"),
            spaceAfter=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Repo",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=16,
            textColor=colors.HexColor("#204e40"),
            spaceAfter=20,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#7d8d75"),
            spaceAfter=14,
        )
    )
    repo = "https://github.com/yoman12357/manifest-customs"
    story = [Paragraph(f'<link href="{repo}">{repo}</link>', styles["Repo"])]
    text = (ROOT / "docs/TDD.md").read_text(encoding="utf-8")
    for block in text.split("\n\n"):
        block = block.strip()
        if not block or block.startswith("GitHub:"):
            continue
        if block.startswith("# "):
            story.append(Paragraph(escape(block[2:]), styles["ManifestTitle"]))
        elif block.startswith("## "):
            if re.match(r"## (3|5|7|9)\.", block):
                story.append(PageBreak())
            story.append(Paragraph(escape(block[3:]), styles["Section"]))
        else:
            story.append(Paragraph(escape(block.replace("\n", " ")), styles["Copy"]))
    for name, title, caption, width in [
        (
            "desktop-review.png",
            "Design evidence / Desktop review",
            "The authenticated original and editable fields stay adjacent. Every draft remains unconfirmed until checked by a reviewer.",
            490,
        ),
        (
            "mobile-checks.png",
            "Design evidence / Phone review",
            "At 390 px the navigation collapses, actions stack, and each failed cross-check remains legible without page-level horizontal scrolling.",
            235,
        ),
        (
            "desktop-overview.png",
            "Design evidence / Operations overview",
            "Database-backed shipment counts, search and status filters provide a focused starting point.",
            490,
        ),
    ]:
        path = ROOT / "docs/screenshots" / name
        if not path.exists():
            continue
        story.extend(
            [
                PageBreak(),
                Paragraph(title, styles["Section"]),
                Paragraph(caption, styles["Caption"]),
            ]
        )
        reader = ImageReader(str(path))
        w, h = reader.getSize()
        height = width * h / w
        if height > 650:
            width *= 650 / height
            height = 650
        story.append(Image(str(path), width=width, height=height, hAlign="LEFT"))

    def page(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#dce4d6"))
        canvas.line(47, 43, 548, 43)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8b9980"))
        canvas.drawString(48, 29, "MANIFEST / TECHNICAL DESIGN / 02 NOV 2026")
        canvas.drawRightString(547, 29, str(doc.page))

    SimpleDocTemplate(
        str(pdf),
        pagesize=(595, 842),
        rightMargin=48,
        leftMargin=48,
        topMargin=45,
        bottomMargin=58,
        title="Manifest — Technical Design",
        author="Aryan",
    ).build(story, onFirstPage=page, onLaterPages=page)
    deployment = (ROOT / "deployment.md").read_bytes()
    (dest / "deployment.md").write_bytes(deployment)
    zip_path = dest / "Manifest_Submission.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, "Manifest_TDD.pdf")
        z.writestr("deployment.md", deployment)
    with zipfile.ZipFile(zip_path) as z:
        assert z.namelist() == ["Manifest_TDD.pdf", "deployment.md"]
        assert z.testzip() is None
    assert zip_path.stat().st_size < 25 * 1024 * 1024
    print(f"Created {zip_path} ({zip_path.stat().st_size:,} bytes); exactly two files.")


if __name__ == "__main__":
    build()
