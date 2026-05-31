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
        "Multi-model agreement is useful evidence, but it is not proof of correctness. ConsensusScope exposes when to accept, inspect, or route a multi-LLM decision for human review.",
    )

    doc.add_heading("1. Page-by-page Recording Plan", level=1)
    add_timeline_table(
        doc,
        [
            ("0:00-0:20", "Page 1", "Open Home / System Overview. Keep the pointer near the title and pipeline.", "Problem and premise"),
            ("0:20-0:45", "Page 2", "Show API Configuration. Then click Live Question Mode and show task input.", "Live workflow and API safety"),
            ("0:45-1:10", "Page 3", "Click Sample Audit Mode. Select a saved benchmark sample and show model outputs.", "Structured traces"),
            ("1:10-1:35", "Page 4", "Click Adjudication Comparison. Point to majority vote, fixed judge, dynamic judge.", "Adjudication layer"),
            ("1:35-2:00", "Page 5", "Click Risk Dashboard. Point to low-risk accuracy and high-risk error rate.", "Risk stratification"),
            ("2:00-2:20", "Page 7/8", "Click Case Explorer, then Report Export. Show case inspection and download buttons.", "Audit and export"),
            ("2:20-2:30", "Page 1", "Return to Home. Stop moving the mouse and close with one sentence.", "Conclusion"),
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
        "ConsensusScope is an interactive observability tool for risk-aware multi-LLM adjudication. It starts from a simple premise: multi-model agreement is useful evidence, but agreement alone is not proof of correctness.",
    )

    add_segment(
        doc,
        "0:20-0:45",
        "API configuration and live mode",
        [
            "Move to the sidebar API Configuration panel.",
            "Show Mode A and Mode B without typing any real API key.",
            "Click Page 2: Live Question Mode.",
            "Show the task-type selector, question input, model selection area, and Run Live Comparison button.",
        ],
        "The system supports two API modes. Mode A is for controlled local demos using configured environment variables or deployment secrets. Mode B is for public deployment, where users provide their own temporary API keys. API keys are not written into the paper and are not hard-coded in the repository.",
    )

    add_segment(
        doc,
        "0:45-1:10",
        "Structured multi-model traces",
        [
            "Click Page 3: Sample Audit Mode.",
            "Select a dataset such as FEVER or CommonsenseQA.",
            "Select a sample ID and scroll to the model-output area.",
            "Point to answer, reason, confidence, and evidence fields.",
        ],
        "Each model output is stored in a unified schema, including answer, rationale, confidence, evidence, raw output, and parse metadata. This lets us inspect not only the final answer, but also whether models agree, whether evidence is available, and whether confidence signals are reliable.",
    )

    add_segment(
        doc,
        "1:10-1:35",
        "Adjudication comparison",
        [
            "Click Page 4: Adjudication Comparison.",
            "Point first to Majority Vote.",
            "Move to Fixed Judge.",
            "Move to Dynamic Rule-Based Judge.",
        ],
        "ConsensusScope compares three adjudication strategies. Majority vote is the frequency-based baseline. The fixed judge uses a configured judge model, by default deepseek-chat, and it does not see the gold answer. The rule-based dynamic judge uses deploy-time signals such as agreement rate, answer diversity, confidence distribution, evidence availability, minority warnings, and parse errors.",
    )

    add_segment(
        doc,
        "1:35-2:00",
        "Risk dashboard and evaluation",
        [
            "Click Page 5: Risk Dashboard.",
            "Point to the low, medium, and high risk levels.",
            "Pause near the low-risk accuracy number.",
            "Pause near the high-risk error-rate number.",
        ],
        "In the 1000-sample pilot, we avoid a single mixed macro-F1 score because TruthfulQA, FEVER, and CommonsenseQA have different answer spaces. The key result is risk stratification: low-risk dynamic decisions reach 91.8 percent accuracy, while high-risk decisions concentrate errors with a 95.2 percent error rate.",
    )

    add_segment(
        doc,
        "2:00-2:20",
        "Case explorer and report export",
        [
            "Click Page 7: Case Explorer.",
            "Open the Inspect case selector and choose one case.",
            "Click Page 8: Report Export.",
            "Show system_summary.json, method_metrics.csv, and risk_labels.csv download buttons.",
        ],
        "The case explorer supports sample-level auditing, while the export page packages reports and CSV files for reproducibility. Offline labels such as false consensus or minority-correct cases are used only when gold labels are available; live deployment relies on observable risk signals.",
    )

    add_segment(
        doc,
        "2:20-2:30",
        "Closing",
        [
            "Click Page 1: Home / System Overview.",
            "Stop moving the mouse.",
            "Leave one second of silence after the final sentence before stopping the recording.",
        ],
        "ConsensusScope is not a truth oracle. It is a reliability layer that helps researchers and practitioners decide when a multi-LLM system should answer, warn, re-check, or route the case for human review.",
    )

    doc.add_heading("3. Presenter Checklist", level=1)
    for item in [
        "Use English narration for international conference submission.",
        "Keep the video at or below 2 minutes 30 seconds.",
        "Do not type or reveal real API keys.",
        "Do not claim that the system knows false consensus at deployment time.",
        "Say clearly that offline diagnostic labels require gold labels.",
        "Do not frame the dynamic judge as a stronger model; frame it as risk stratification and review routing.",
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
