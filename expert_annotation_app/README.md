# ConsensusScope Expert Annotation App

This is an independent research annotation tool for collecting expert gold
labels on AI-generated ESL writing feedback. It is separate from the main
ConsensusScope demo and is not part of the paper UI.

## 中文使用说明

这个网页给英语教师做人工标注用，不是主 demo，也不是自动作文评分器。

教师正式标注时只走一条线：

```text
开始标注 -> 作文整体评价 -> 逐条反馈判断 -> 反馈风险判断 -> 查看进度 -> 导出结果
```

教师只需要选择：

- 教师编号：`1` 或 `2`
- 批次编号：`1` 或 `2`

默认使用盲标模式。盲标模式不会显示系统风险等级、推荐动作、模型一致性、模型名称或 ConsensusScope 决策，避免影响教师判断。

“高级选项（研究者使用）”中的系统辅助信息只用于研究者事后核查，不建议教师正式标注时打开。

作文备注为选填项；判断理由仍为必填项，因为后续需要分析教师为什么接受、修改或拒绝某条 AI 反馈。

## Purpose

English teachers can read anonymized ESL essays and item-level AI feedback, then
label whether the feedback is correct, preserves the student's intended meaning,
is safe to show to students, and should be accepted, edited, rejected, or marked
as uncertain.

The teacher-facing workflow uses **Blind Annotation Mode** by default. In blind
mode, the app hides system `risk_level`, `recommended_action`, model agreement,
model name, and ConsensusScope routing decisions.

Assisted Review Mode is kept only as a researcher/admin option for later
inspection. Teachers should normally follow the single line:

```text
Start Annotation -> Essay Annotation -> Feedback Annotation -> Feedback Safety Check -> Progress -> Export
```

Teachers only need to select a teacher ID (`1` or `2`) and a batch ID (`1` or
`2`) before annotation.

The interface supports English and Chinese switching from the sidebar. Exported
CSV/JSON field names and label values remain in English canonical form for
analysis.

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
Root-level Streamlit secrets are read through environment variables by the app.
Do not hard-code it in the source code.

## Pages

1. Expert Session
2. Essay Annotation
3. Feedback Annotation
4. Feedback Safety Check
5. Progress
6. Export

## Data Inputs

Sample CSV files are stored in `sample_data/`:

- `essays.csv`
- `feedback_items.csv`
- `routing_results.csv` optional, used only in Assisted Review Mode

Use only anonymized ESL writing data. Do not upload names, student IDs, email
addresses, class names, school identifiers, demographic details, or any other
personally identifying information.

## Storage

For formal teacher annotation, use Supabase/PostgreSQL external storage. Run
the repository-level SQL file before deployment:

```text
consensusscope_supabase_schema.sql
```

Then configure Streamlit Secrets:

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

When these secrets are present, the app writes to these Supabase tables:

- `consensusscope_expert_sessions`
- `consensusscope_essay_annotations`
- `consensusscope_feedback_decisions`
- `consensusscope_feedback_safety_checks`
- `consensusscope_annotation_logs`

If Supabase is not configured, the app falls back to local SQLite for local
development only:

```text
annotation_data/expert_annotations.sqlite3
```

Local SQLite is not durable on Streamlit Community Cloud and should not be used
as the main research data store.

The local SQLite fallback creates these tables:

- `expert_sessions`
- `essay_annotations`
- `feedback_decisions`
- `feedback_safety_checks`
- `annotation_logs`

Each annotation record stores `expert_id`, `batch_id`, `created_at`,
`updated_at`, and `duration_seconds`.

## Export

The Export page provides:

- `essay_annotations.csv`
- `feedback_decisions.csv`
- `feedback_safety_checks.csv`
- `annotation_logs.csv`
- `combined_annotations.json`

You can download files in the browser or write them to the local `exports/`
folder.

## Research And Privacy Boundary

This tool is only for research annotation. It is not an automatic essay scorer,
not a teacher replacement, and not a student-facing grading system.

Only anonymized student writing should be used. Do not store or upload PII.
