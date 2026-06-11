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
4. Set the site password as a root-level Streamlit Secret:

```toml
EXPERT_ANNOTATION_PASSWORD = "replace-with-a-private-password"
```

5. Share the deployed URL and password only with participating teachers.

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
   - Feedback Likert Questionnaire
   - Progress
   - Export
6. Researcher exports CSV/JSON files from Export.

## 中文给教师的流程

正式标注时请按左侧页面从上到下完成：

```text
开始标注 -> 逐条反馈 1-5 分问卷 -> 查看进度 -> 导出结果
```

教师只需要选择教师编号 `1` 或 `2`，批次编号 `1` 或 `2`。默认盲标即可；“高级选项（研究者使用）”不要打开。
每条 AI 反馈只需要按正确性、保留原意、学生可见性、有用性、清晰可操作性和直接放行六个维度打 1-5 分。

## Important Storage Boundary

This deployment uses local SQLite inside the Streamlit app container. It is
simple and avoids external database failures, but Streamlit Community Cloud can
reset local container storage. For formal annotation:

- export CSV/JSON files from the Export page after each teacher session;
- back up exported files outside Streamlit Cloud;
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
