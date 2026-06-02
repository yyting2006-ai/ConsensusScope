from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ConsensusScope_EMNLP_demo_script_2min30_en.docx"


def set_run_font(run, font_name: str = "Arial", size: int | None = None, bold: bool | None = None):
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def set_style_font(style, font_name: str, size: int, color: str | None = None, bold: bool | None = None):
    style.font.name = font_name
    style._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    style.font.size = Pt(size)
    if color:
        style.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        style.font.bold = bold


def shade_cell(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_width(table, width_dxa: int = 9360):
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(width_dxa))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")


def set_cell_text(cell, text: str, bold: bool = False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.08
    r = p.add_run(text)
    set_run_font(r, size=9, bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    set_cell_margins(cell)


def add_labeled_para(doc: Document, label: str, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    r1 = p.add_run(label)
    set_run_font(r1, size=10, bold=True)
    r2 = p.add_run(text)
    set_run_font(r2, size=10)


def add_timeline_table(doc: Document, rows: list[tuple[str, str, str, str]]):
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.autofit = False
    set_table_width(table)
    headers = ["Time", "Page", "Screen Action", "Narration Focus"]
    widths = [0.8, 1.3, 2.9, 1.3]
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.width = Inches(widths[idx])
        set_cell_text(cell, header, bold=True)
        shade_cell(cell, "E8EEF5")
    for row_data in rows:
        row = table.add_row()
        for idx, text in enumerate(row_data):
            cell = row.cells[idx]
            cell.width = Inches(widths[idx])
            set_cell_text(cell, text)
    doc.add_paragraph()


def add_segment(doc: Document, time: str, title: str, actions: list[str], narration: str):
    h = doc.add_paragraph(style="Heading 2")
    r = h.add_run(f"{time}  {title}")
    set_run_font(r, size=12, bold=True)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Screen actions:")
    set_run_font(r, size=10, bold=True)
    for action in actions:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(action)
        set_run_font(r, size=9)

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.right_indent = Inches(0.05)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F4F6F9")
    p_pr.append(shd)
    r1 = p.add_run("Narration: ")
    set_run_font(r1, size=10, bold=True)
    r2 = p.add_run(narration)
    set_run_font(r2, size=10)


def build_doc() -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = Inches(0.85)
    sec.bottom_margin = Inches(0.85)
    sec.left_margin = Inches(0.85)
    sec.right_margin = Inches(0.85)

    styles = doc.styles
    set_style_font(styles["Normal"], "Arial", 10, "000000")
    styles["Normal"].paragraph_format.space_after = Pt(5)
    styles["Normal"].paragraph_format.line_spacing = 1.08
    set_style_font(styles["Heading 1"], "Arial", 15, "2E74B5", True)
    set_style_font(styles["Heading 2"], "Arial", 12, "2E74B5", True)
    set_style_font(styles["Heading 3"], "Arial", 11, "1F4D78", True)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(3)
    r = title.add_run("ConsensusScope EMNLP Demo Screencast Script")
    set_run_font(r, size=20, bold=True)
    r.font.color.rgb = RGBColor.from_string("0B2545")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(10)
    r = subtitle.add_run("English version · 2 minutes 30 seconds · with screen actions")
    set_run_font(r, size=11)
    r.font.color.rgb = RGBColor.from_string("555555")

    add_labeled_para(
        doc,
        "Recording target: ",
        "International conference submission. Use English narration. Keep the final video at or below 2 minutes 30 seconds.",
    )
    add_labeled_para(
        doc,
        "Main message: ",
        "AI writing feedback can be fluent but unsafe. ConsensusScope routes ESL writing feedback into low-risk auto-accept and teacher-review queues before students see unsafe suggestions.",
    )

    doc.add_heading("1. Page-by-page Recording Plan", level=1)
    add_timeline_table(
        doc,
        [
            ("0:00-0:20", "Page 1", "Open Review Workspace. Keep the pointer near the teacher-facing question and workflow.", "Problem and premise"),
            ("0:20-0:45", "Page 2", "Click Essay Review. Show the assignment prompt, essay, and routing summary.", "System overview"),
            ("0:45-1:15", "Page 3", "Click Feedback Detail. Show target span, suggestion, risk, routing explanation, and teacher actions.", "Feedback detail"),
            ("1:15-1:45", "Page 4", "Click Teacher Queue. Point to filters and high-risk items.", "Teacher review queue"),
            ("1:45-2:10", "Page 5", "Click Writing Rubric. Point to deploy-time routing rules.", "Routing rules"),
            ("2:10-2:25", "Page 6", "Click Reports and show the report preview.", "Export"),
            ("2:25-2:30", "Page 1/6", "Stop moving the mouse and close with one sentence.", "Conclusion"),
        ],
    )

    doc.add_heading("2. Full English Narration Script", level=1)
    add_segment(
        doc,
        "0:00-0:20",
        "Opening",
        [
            "Click Page 1: Review Workspace in the sidebar.",
            "Keep the pointer near the title ConsensusScope.",
            "Briefly move the pointer over the teacher-facing workflow.",
        ],
        "AI writing feedback can be fluent but unsafe. A model may fix a local grammar issue while changing a student's intended meaning, adding unsupported content, or overcorrecting a reasonable ESL draft.",
    )

    add_segment(
        doc,
        "0:20-0:45",
        "System overview",
        [
            "Click Page 2: Essay Review.",
            "Show the anonymized synthetic essay.",
            "Point to the assignment prompt and routing summary.",
        ],
        "ConsensusScope routes AI-generated ESL writing feedback before it reaches students. Low-risk local edits can be accepted, while feedback that may change meaning or require pedagogical judgment goes to the teacher queue.",
    )

    add_segment(
        doc,
        "0:45-1:15",
        "Feedback detail",
        [
            "Click Page 3: Feedback Detail.",
            "Point to the high-risk thesis-reversal example.",
            "Show routing explanation and teacher action buttons.",
        ],
        "Each feedback item has a unified schema: issue type, target span, suggestion, student-facing draft, risk level, routing reason, and review evidence.",
    )

    add_segment(
        doc,
        "1:15-1:45",
        "Teacher review queue",
        [
            "Click Page 4: Teacher Queue.",
            "Point to high-risk meaning-change and unsupported-claim items.",
            "Show risk, issue type, and status filters.",
        ],
        "The teacher queue prioritizes high-risk feedback first. Teachers can filter by risk, issue type, and status, so the system supports human review rather than hiding uncertainty behind one automatic decision.",
    )

    add_segment(
        doc,
        "1:45-2:10",
        "Writing rubric",
        [
            "Click Page 5: Writing Rubric.",
            "Point to meaning preservation, local language edit, task response, and tone rules.",
            "Mention that the router uses deploy-time signals, not hidden gold labels.",
        ],
        "The Writing Rubric page makes routing rules inspectable. The system uses deploy-time signals such as meaning preservation, local edit scope, task response, organization, tone, and parse quality.",
    )

    add_segment(
        doc,
        "2:05-2:25",
        "Report export",
        [
            "Click Page 6: Reports.",
            "Show the teacher-readable report preview.",
            "Point to accepted edits, review-routed items, routing reasons, and limitations.",
        ],
        "The report exports a teacher-readable audit trail with accepted edits, review-routed items, routing reasons, and limitations.",
    )

    add_segment(
        doc,
        "2:20-2:30",
        "Closing",
        [
            "Return to Page 1 or stay on Report Export.",
            "Stop moving the mouse.",
            "Leave one second of silence after the final sentence before stopping the recording.",
        ],
        "ConsensusScope helps teachers decide when AI feedback is safe to show and when it needs human review.",
    )

    doc.add_heading("3. Presenter Checklist", level=1)
    for item in [
        "Use English narration for international conference submission.",
        "Keep the video at or below 2 minutes 30 seconds.",
        "Do not type or reveal real API keys.",
        "Do not claim teacher-study or classroom annotation results that are not in the data.",
        "Do not frame ConsensusScope as an automatic essay scorer or teacher replacement.",
        "Keep auxiliary QA pages clearly secondary to the ESL literary-feedback workflow.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(item)
        set_run_font(r, size=10)

    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = footer.add_run("ConsensusScope EMNLP demo script · English · 2:30")
    set_run_font(r, size=8)
    r.font.color.rgb = RGBColor.from_string("777777")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)


if __name__ == "__main__":
    build_doc()
    print(OUT)
