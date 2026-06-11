# ConsensusScope Expert Annotation App

This is an independent research annotation tool for collecting teacher
judgments on AI-generated ESL writing feedback. It is separate from the main
ConsensusScope demo and is not a student-facing grading system.

## 中文使用说明

这个网页用于让英语教师判断 AI 生成的英语写作反馈是否可靠。正式 pilot
最多只邀请两位教师，每位教师只需要用 1-5 分问卷逐条评价 AI 反馈。

教师正式标注只走一条线：

```text
开始标注 -> 逐条反馈 1-5 分问卷 -> 查看进度 -> 导出结果
```

教师只需要选择：

- 教师编号：`1` 或 `2`
- 批次编号：`1` 或 `2`

批次含义：

- `1`：原始 pilot 批次，12 条 AI feedback items。
- `2`：新增扩展批次，18 条 AI feedback items。

如果老师已经完成过批次 `1`，请继续使用同一个教师编号，选择批次 `2`
完成新增样本。不要让老师重复标注已经完成的批次。

默认使用盲标模式。盲标模式不会显示系统风险等级、推荐动作、模型一致性、
模型名称或 ConsensusScope 决策，避免影响教师判断。

“高级选项（研究者使用）”只适合研究者事后核查系统判断，正式请老师标注时
不要打开。

## What Teachers Rate

Each AI feedback item is scored on six 1-5 dimensions:

- correctness score: whether the feedback is correct;
- meaning preservation score: whether it preserves the student's intended
  meaning;
- student readiness score: whether it is safe to show to a student;
- usefulness score: whether it helps revision;
- clarity/actionability score: whether it is clear and actionable;
- direct-release score: whether it can be released without teacher review.

Scale anchors:

```text
1 = clearly negative / unsafe / not ready
3 = uncertain
5 = clearly positive / safe / ready
```

No categorical labels, written rationales, or teacher comments are required in
the formal pilot.

## Run

From this folder:

```bash
streamlit run app.py --server.port 8503
```

Then open:

```text
http://localhost:8503
```

For a dedicated teacher-facing website, deploy this as a separate Streamlit app
with main file path:

```text
expert_annotation_app/app.py
```

Optional password protection:

```toml
EXPERT_ANNOTATION_PASSWORD = "replace-with-a-private-password"
```

Set this as a root-level Streamlit Secret or as a local environment variable.
Do not hard-code it in the source code.

## Pages

1. Expert Session
2. Feedback Likert Questionnaire
3. Progress
4. Export

## Data Inputs

Sample CSV files are stored in `sample_data/`:

- `essays.csv`
- `feedback_items.csv`, including 30 feedback items across two annotation
  batches
- `routing_results.csv` optional, used only when researcher-assisted signals
  are enabled

Use only anonymized ESL writing data. Do not upload names, student IDs, email
addresses, class names, school identifiers, demographic details, or any other
personally identifying information.

## Storage

The current expert annotation website uses local SQLite storage:

```text
annotation_data/expert_annotations.sqlite3
```

On Streamlit Community Cloud, local SQLite is convenient for the demo but may be
reset by the hosting platform. For formal teacher annotation, export the
CSV/JSON files from the Export page after each teacher session and back them up
outside Streamlit Cloud.

The primary table for the two-teacher pilot is:

- `likert_feedback_ratings`

The app also keeps legacy tables from the earlier categorical prototype for
backward compatibility, but they are not part of the current teacher-facing
workflow.

Each exported rating record stores `expert_id`, `batch_id`, `created_at`,
`updated_at`, and `duration_seconds`.

## Export

The Export page provides:

- `likert_feedback_ratings.csv`
- `annotation_logs.csv`
- `combined_annotations.json`

You can download files in the browser or write them to the local `exports/`
folder.

## Analyze A Two-Teacher Pilot

After exporting the ratings, run:

```bash
PYTHONPATH=. python3 ../scripts/analyze_teacher_likert_pilot.py \
  --ratings exports_or_combined_csv_folder \
  --routing sample_data/routing_results.csv
```

The analysis reports teacher score averages, two-teacher agreement when both
teachers rated the same items, and how well system routing covers feedback that
teachers marked as needing review.

For the expanded pilot, put all exported `likert_feedback_ratings*.csv` files
from both teachers and both batches into one folder. The analysis script can
read that folder directly.

## Research And Privacy Boundary

This tool is only for research annotation. It is not an automatic essay scorer,
not a teacher replacement, and not a student-facing grading system.

Only anonymized student writing should be used. Do not store or upload PII.
