# Expert Annotation Website Deployment

This app should be deployed as a dedicated expert annotation website, separate
from the main ConsensusScope demo.

## Recommended Website Setup

Use a separate Streamlit app:

```text
Main file path: expert_annotation_app/app.py
Port for local test: 8503
```

Local test:

```bash
cd expert_annotation_app
streamlit run app.py --server.port 8503
```

Public or private web deployment:

1. Push the repository to GitHub.
2. Create a separate Streamlit Community Cloud app.
3. Set the main file path to `expert_annotation_app/app.py`.
4. Run `consensusscope_supabase_schema.sql` in Supabase SQL Editor.
5. Set external storage and site password as root-level Streamlit Secrets:

```toml
EXPERT_ANNOTATION_PASSWORD = "replace-with-a-private-password"
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

6. Share the deployed URL and password only with participating teachers.

Do not hard-code the password in `app.py`, README files, the paper, screenshots,
or video recordings.

## Suggested Teacher Workflow

1. Teacher opens the expert annotation URL.
2. Teacher enters the site password.
3. Teacher creates or selects:
   - teacher ID: `1` or `2`
   - batch ID: `1` or `2`
4. Teacher uses the default Blind Annotation Mode.
5. Teacher completes:
   - Expert Session
   - Essay Annotation
   - Feedback Annotation
   - Feedback Safety Check
   - Progress
   - Export
6. Researcher exports CSV/JSON files from Export.

## 中文给教师的流程

正式标注时请按左侧页面从上到下完成：

```text
开始标注 -> 作文整体评价 -> 逐条反馈判断 -> 反馈风险判断 -> 查看进度 -> 导出结果
```

教师只需要选择教师编号 `1` 或 `2`，批次编号 `1` 或 `2`。默认盲标即可；“高级选项（研究者使用）”不要打开。

## Important Storage Boundary

This version supports Supabase/PostgreSQL external storage. When `SUPABASE_URL`
and `SUPABASE_SERVICE_ROLE_KEY` are configured, teacher annotations are written
to the external database.

SQLite is kept only as a local development fallback. It is not durable on
Streamlit Community Cloud and should not be used as the main research data
store.

For long-term multi-teacher data collection:

- keep the same Streamlit interface;
- use PostgreSQL/Supabase or another institution-approved managed database;
- keep Blind Annotation Mode unchanged;
- keep exports in the same CSV/JSON schema.

## Privacy Rules

Only upload anonymized ESL writing data. Do not upload:

- names
- student IDs
- email addresses
- class names
- school identifiers
- demographic details
- any other personally identifying information

This website is only for research annotation. It is not an automatic essay
scorer, not a teacher replacement, and not a student-facing grading system.
