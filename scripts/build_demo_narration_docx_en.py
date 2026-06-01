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
        "AI writing feedback can be fluent but unsafe. ConsensusScope routes ESL comparative-literature feedback into low-risk auto-accept and teacher-review queues with literary knowledge evidence.",
    )

    doc.add_heading("1. Page-by-page Recording Plan", level=1)
    add_timeline_table(
        doc,
        [
            ("0:00-0:20", "Page 1", "Open Home / System Overview. Keep the pointer near the title and workflow.", "Problem and premise"),
            ("0:20-0:45", "Page 2", "Click ESL Feedback Review. Show the essay input and reviewer source selector.", "System overview"),
            ("0:45-1:10", "Page 2", "Run the no-API demo and open Knowledge Evidence.", "Knowledge grounding"),
            ("1:10-1:40", "Page 2/3", "Show Teacher View, Adjudication Trace, then Knowledge Grounding & Teacher Queue.", "Feedback routing"),
            ("1:40-2:05", "Page 3", "Point to risk level, priority, model agreement, and KG support.", "Teacher review queue"),
            ("2:05-2:25", "Page 8", "Click Report Export and show the report download buttons.", "Export"),
            ("2:25-2:30", "Page 1/8", "Stop moving the mouse and close with one sentence.", "Conclusion"),
        ],
    )

    doc.add_heading("2. Full English Narration Script", level=1)
    add_segment(
        doc,
        "0:00-0:20",
        "Opening",
        [
            "Click Page 1: Home / System Overview in the sidebar.",
            "Keep the pointer near the title ConsensusScope.",
            "Briefly move the pointer over the system pipeline.",
        ],
        "AI writing feedback can be fluent but unsafe. In ESL comparative-literature essays, a model may fix grammar correctly while changing literary facts, character relations, or the student's interpretation.",
    )

    add_segment(
        doc,
        "0:20-0:45",
        "System overview",
        [
            "Move to the sidebar API Configuration panel.",
            "Show Mode A and Mode B without typing any real API key.",
            "Click Page 2: ESL Feedback Review.",
            "Show the essay input, reviewer source selector, and Run Knowledge-Grounded Feedback button.",
        ],
        "ConsensusScope compares multiple LLM feedback outputs and routes each suggestion into either low-risk auto-accept or teacher review. It is not an automatic essay scorer and it does not replace teacher judgment.",
    )

    add_segment(
        doc,
        "0:45-1:10",
        "Knowledge grounding",
        [
            "Run the no-API deterministic feedback demo.",
            "Open the Knowledge Evidence tab.",
            "Point to author, genre, character, theme, and publication-year rows.",
        ],
        "The system retrieves evidence from a curated literary knowledge graph, including author, work, genre, central characters, themes, and publication year. These triples make factual feedback inspectable.",
    )

    add_segment(
        doc,
        "1:10-1:40",
        "Feedback adjudication",
        [
            "Open the Teacher View tab.",
            "Point to the auto-accepted preview.",
            "Open the Adjudication Trace tab.",
            "Click Page 3: Knowledge Grounding & Teacher Queue.",
        ],
        "Low-risk local grammar or style edits can be accepted, but suggestions about authorship, genre, character identity, thesis statements, or interpretation remain in the teacher-review queue.",
    )

    add_segment(
        doc,
        "1:40-2:05",
        "Teacher review queue",
        [
            "Point to risk level, priority, agreement, and KG support fields.",
            "Briefly mention the auxiliary QA pages only if visible.",
            "Avoid presenting the old QA benchmark as the main system story.",
        ],
        "The teacher review queue shows risk level, priority, model agreement, knowledge support, and a short explanation for why human review is recommended. The system also includes auxiliary multi-model QA audit pages, but this demo focuses on ESL literary feedback.",
    )

    add_segment(
        doc,
        "2:05-2:25",
        "Report export",
        [
            "Click Page 8: Report Export.",
            "Show the literary feedback report download.",
            "Show system_summary.json and CSV export buttons.",
        ],
        "The final page exports a Markdown feedback report and structured JSON or CSV files so the decision process can be inspected and reproduced.",
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
        "ConsensusScope helps decide when AI feedback requires human review.",
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
