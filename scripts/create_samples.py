"""Authored fictional PDFs: safe to redistribute, with known facts and disagreements."""

import json
from hashlib import sha256
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples"
DOCUMENTS = [
    {
        "filename": "cedar-trial-report.pdf",
        "title": "The Cedar Sleep Study",
        "subtitle": "Primary report | Fictional research fixture",
        "pages": [
            [
                (
                    "Study overview",
                    "The Cedar trial enrolled 120 adults aged 18 to 30. Participants were randomly assigned to a sleep-extension group or a control group. The trial lasted six weeks.",
                ),
                (
                    "Primary finding",
                    "In the Cedar trial, the sleep-extension group improved its attention score by 12 points after six weeks. The control group improved by 2 points. The primary report describes a positive effect on attention.",
                ),
                (
                    "Sleep duration",
                    "Average nightly sleep increased from 6.2 hours to 7.5 hours in the sleep-extension group. Sleep was measured using wrist-worn activity monitors.",
                ),
            ],
            [
                (
                    "Limitations",
                    "The Cedar trial was conducted at a single university. Participants knew their group assignment. The small sample and short follow-up limit generalization to older adults.",
                ),
                (
                    "What was not measured",
                    "The Cedar trial did not measure school grades, long-term memory, or mortality. It did not recruit children. No claim about exam performance can be drawn from this trial.",
                ),
                (
                    "Data availability",
                    "All numbers in this document are fictional and were written to test VeritasAI. This document is not medical advice and is not a published study.",
                ),
            ],
        ],
    },
    {
        "filename": "cedar-reanalysis.pdf",
        "title": "Cedar: An Independent Reanalysis",
        "subtitle": "Audit note | Fictional research fixture",
        "pages": [
            [
                (
                    "Same trial, different conclusion",
                    "This reanalysis examined the same 120 adults in the six-week Cedar trial. The audit identified a scoring error in the attention test.",
                ),
                (
                    "Corrected result",
                    "After correcting the scoring error, the Cedar sleep-extension group improved its attention score by 2 points, not 12 points. The control group also improved by 2 points. The reanalysis found no improvement in attention relative to the control group.",
                ),
                (
                    "What changed",
                    "The reanalysis agrees that nightly sleep increased to 7.5 hours. It disputes the attention-score result in the primary report. Both documents refer to the same participants, period, and attention test.",
                ),
                (
                    "Purpose of this document",
                    "This entire document is fictional. It exists to test whether an assistant preserves conflicting evidence instead of selecting only the most convenient source.",
                ),
            ]
        ],
    },
    {
        "filename": "willow-observation.pdf",
        "title": "The Willow Reading Project",
        "subtitle": "Observation summary | Fictional research fixture",
        "pages": [
            [
                (
                    "Study overview",
                    "The Willow project observed 85 adults aged 50 to 65 over four weeks. Researchers recorded reading duration and self-reported concentration. The project was observational, not randomized.",
                ),
                (
                    "Finding",
                    "Adults who read for at least 30 minutes per day reported better concentration. The association does not establish that reading caused the improvement.",
                ),
                (
                    "Different population",
                    "The Willow project did not study sleep extension. Its participants and outcomes differ from those in the Cedar trial. The two projects should not be treated as directly contradictory.",
                ),
                (
                    "Purpose of this document",
                    "This document is fictional and is included as a retrieval distractor and a test of causal overstatement.",
                ),
            ]
        ],
    },
]


def footer(canvas, document):
    canvas.setStrokeColor(colors.HexColor("#dcd8e5"))
    canvas.line(52, 53, 543, 53)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#8d849a"))
    canvas.drawString(52, 37, "VERITASAI  /  AUTHORED FICTIONAL FIXTURE  /  CC0")
    canvas.drawRightString(543, 37, f"{document.page}")


def main():
    OUT.mkdir(exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Brand",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#847299"),
            spaceAfter=28,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            fontName="Times-Roman",
            fontSize=30,
            leading=34,
            textColor=colors.HexColor("#332c3e"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Sub",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#93899e"),
            spaceAfter=25,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#574965"),
            spaceBefore=20,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Copy",
            fontName="Helvetica",
            fontSize=11,
            leading=18,
            textColor=colors.HexColor("#67616d"),
            spaceAfter=8,
            alignment=TA_LEFT,
        )
    )
    records = []
    for doc in DOCUMENTS:
        story = []
        for number, page in enumerate(doc["pages"]):
            if number:
                story.append(PageBreak())
            story += [
                Paragraph("VERITASAI / SAMPLE LIBRARY", styles["Brand"]),
                Paragraph(doc["title"], styles["DocTitle"]),
                Paragraph(doc["subtitle"], styles["Sub"]),
            ]
            for title, body in page:
                story += [
                    Paragraph(title, styles["Section"]),
                    Paragraph(body, styles["Copy"]),
                ]
        path = OUT / doc["filename"]
        SimpleDocTemplate(
            str(path),
            pagesize=(595, 842),
            leftMargin=52,
            rightMargin=52,
            topMargin=48,
            bottomMargin=70,
            title=doc["title"],
            author="VeritasAI authored fixtures",
        ).build(story, onFirstPage=footer, onLaterPages=footer)
        records.append(
            {
                "filename": doc["filename"],
                "title": doc["title"],
                "pages": len(doc["pages"]),
                "license": "CC0-1.0",
                "fictional": True,
                "sha256": sha256(path.read_bytes()).hexdigest(),
            }
        )
        print("Created", doc["filename"])
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "documents": records,
                "notice": "Entirely fictional authored fixtures. Not published research or real company data.",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
