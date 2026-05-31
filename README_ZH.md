# 面向多大模型协同决策的可靠性评估与动态裁决机制研究

这是一个大学生创新训练项目的 Python 实验系统骨架。项目不训练大模型，而是研究多个大语言模型在同一批公开数据集问题上的协同决策可靠性。

系统目标：

- 整理 TruthfulQA、FEVER、CommonsenseQA 等公开数据集样本；
- 调用 DeepSeek、Qwen、GLM、Kimi，并预留 OpenAI 兼容接口；
- 要求模型以 JSON 输出 `answer`、`reason`、`confidence`、`evidence`；
- 保存全部模型原始输出；
- 实现单模型、 多数投票、固定裁决器、动态裁决机制；
- 部署时计算 agreement rate、answer diversity、confidence distribution、evidence availability、minority warning、parse errors 等风险信号；
- 在离线评估中使用 gold label 标注 true consensus、false consensus、minority correct、confidence mismatch 等诊断标签；
- 按数据集计算 final-answer accuracy，并评估风险分层质量和 review-routing utility；
- 自动生成实验结果表、图表和 Streamlit 可视化原型。

## 环境准备

推荐 Python 3.11。

```bash
cd mllm_reliability_adjudication
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
```

然后在 `.env` 中填写需要使用的 API Key。

## 目录结构

```text
mllm_reliability_adjudication/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── outputs/
│   └── results/
├── reports/
│   └── figures/
├── src/
│   ├── data/
│   ├── llm/
│   ├── prompts/
│   ├── parsing/
│   ├── adjudication/
│   ├── evaluation/
│   ├── visualization/
│   └── storage/
├── scripts/
├── app/
└── tests/
```

## API Key 配置

复制 `.env.example`：

```bash
cp .env.example .env
```

按需填写：

```env
DEEPSEEK_API_KEY=your_key
QWEN_API_KEY=your_key
GLM_API_KEY=your_key
KIMI_API_KEY=your_key
OPENAI_API_KEY=your_key
JUDGE_API_KEY=your_key
```

所有模型客户端均使用 OpenAI-compatible `/chat/completions` 接口。若服务商地址或模型名不同，可修改对应 `*_BASE_URL` 和 `*_MODEL`。

固定裁判使用 `judge` provider：默认 `JUDGE_MODEL=deepseek-chat`，默认 `JUDGE_BASE_URL=https://api.deepseek.com`，API key 从 `JUDGE_API_KEY` 读取。可按需替换为其他 OpenAI-compatible judge model。

## 数据准备

请将公开数据放在以下位置：

```text
data/raw/truthfulqa/TruthfulQA.csv
data/raw/fever/*.jsonl
data/raw/commonsenseqa/*.jsonl
```

构建统一数据集：

```bash
python3 -m src.data.dataset_builder \
  --truthfulqa_n 100 \
  --fever_n 100 \
  --commonsenseqa_n 100 \
  --seed 42
```

输出：

```text
data/processed/clean_dataset.csv
data/processed/dataset_summary.csv
```

## 一键运行完整实验

```bash
python3 scripts/run_pipeline.py \
  --sample_per_dataset 100 \
  --models deepseek qwen glm kimi \
  --limit 100
```

包含固定裁决器：

```bash
python3 scripts/run_pipeline.py \
  --sample_per_dataset 100 \
  --models deepseek qwen glm kimi \
  --run_judge
```

复用已有模型输出，跳过 API 调用：

```bash
python3 scripts/run_pipeline.py \
  --sample_per_dataset 100 \
  --skip_model_calls
```

模型调用支持断点续跑：若 `data/outputs/model_outputs.csv` 中已经存在某个 `sample_id + model` 的成功输出，下一次运行会自动跳过该组合。

## 小规模真实实验（每个数据集 10 条）

构建 30 条以内的小规模样本：

```bash
python3 -m src.data.dataset_builder \
  --truthfulqa_n 10 \
  --fever_n 10 \
  --commonsenseqa_n 10 \
  --seed 42
```

调用四个模型，并启用断点续跑：

```bash
python3 -m src.experiments.run_model_answers \
  --input data/processed/clean_dataset.csv \
  --output data/outputs/model_outputs.csv \
  --models deepseek qwen glm kimi \
  --limit 30 \
  --resume
```

模型回答会逐条写入 `data/outputs/model_outputs.csv`，运行日志写入 `data/outputs/run_log.txt`。如果 API 调用或 JSON 解析失败，系统会保存 `raw_output` 和 `parse_error`，并继续运行后续样本。

## CSV 字段标准

`data/processed/clean_dataset.csv`

```text
id, dataset, task_type, question, options, gold_answer, gold_label, evidence, category, source_file
```

`data/outputs/model_outputs.csv`

```text
sample_id, dataset, task_type, model, answer, reason, confidence, evidence, raw_output, parse_error, prompt, created_at
```

`data/results/majority_vote_results.csv`

```text
sample_id, method, final_answer, vote_distribution, agreement_rate, risk_level, decision_note
```

`data/results/dynamic_decision_results.csv`

```text
sample_id, method, final_answer, reliability_score, risk_level, agreement_rate, avg_confidence, evidence_support_score, answer_diversity, minority_warning, decision_note
```

`data/results/fixed_judge_results.csv`

```text
sample_id, method, final_answer, decision_reason, risk_level, confidence
```

`data/results/risk_labels.csv`

```text
sample_id, risk_labels, majority_answer, correct_models, incorrect_models, majority_is_correct
```

`data/results/method_metrics.csv`

```text
method, accuracy, false_consensus_rate, minority_correct_rate, high_disagreement_rate, confidence_mismatch_rate, sample_count
```

注意：`risk_labels.csv` 中的 `false consensus`、`minority correct`、`true consensus`、`confidence mismatch` 是基于 gold answer/gold label 的离线诊断标签，只用于实验分析和案例检索；真实部署时系统不能提前知道这些标签。

## 固定裁判协议

- 默认模型：`deepseek-chat`，通过 `JUDGE_MODEL` 可覆盖。
- 默认接口：`https://api.deepseek.com`，通过 `JUDGE_BASE_URL` 可覆盖。
- 调用温度：`0.0`。
- 输出字段：`final_answer`、`decision_reason`、`risk_level`、`confidence`。
- 输入内容：sample id、dataset、task type、question、options，以及保存的多模型输出记录。
- 是否看到 gold answer：不看 `gold_answer` / `gold_label`。
- 是否看到其他模型 rationale：会看到其他模型的 `answer`、`reason`、`confidence`、`evidence`，以及解析元数据。
- 是否每个样本都调用：当前保存的 pilot run 对 1000 个评估样本逐样本调用，并保存到 `data/results/fixed_judge_results.csv`。
- 可复现性：CSV 结果随 demo 包发布；如果重新调用外部 judge API，结果可能受模型版本和服务商行为影响。

## 当前论文评价口径

论文中不再使用混合 TruthfulQA / FEVER / CommonsenseQA 标签空间的 macro-F1 作为主结果，而改用三组评价：

1. Final-answer selection accuracy by dataset。
2. Risk stratification quality。
3. Review-routing utility。

## 分步运行

整理数据：

```bash
python3 -m src.data.dataset_builder --truthfulqa_n 100 --fever_n 100 --commonsenseqa_n 100 --seed 42
```

运行多数投票与动态裁决：

```bash
python3 -m src.experiments.run_decisions \
  --samples data/processed/clean_dataset.csv \
  --outputs data/outputs/model_outputs.csv \
  --run_majority \
  --run_dynamic
```

评估结果：

```bash
python3 -m src.experiments.evaluate_results \
  --samples data/processed/clean_dataset.csv \
  --outputs data/outputs/model_outputs.csv \
  --majority data/results/majority_vote_results.csv \
  --dynamic data/results/dynamic_decision_results.csv
```

生成图表和报告：

```bash
python3 -m src.reports.generate_figures
python3 -m src.reports.generate_report
```

## 启动可视化系统

启动本地英文投稿 demo：

```bash
streamlit run app/streamlit_app.py --server.port 8502
```

浏览器打开：

```text
http://localhost:8502
```

当前英文公开原型包含八个页面：

- `Page 1: Home / System Overview`：查看样本、模型输出和裁决器概览。
- `Page 2: Live Question Mode`：现场输入问题，配置 API，选择模型，运行多模型回答，查看动态裁决、风险解释并导出报告。
- `Page 3: Sample Audit Mode`：查看同一问题下多个模型的答案、理由、置信度、证据、多数投票、固定裁判、动态裁决和离线风险标签。
- `Page 4: Adjudication Comparison`：比较 majority vote、fixed judge 和 rule-based dynamic adjudication。
- `Page 5: Risk Dashboard`：查看离线诊断标签分布和风险等级效果。
- `Page 6: Model Reliability Dashboard`：查看保存输出中的模型历史可靠性摘要。
- `Page 7: Case Explorer`：浏览错误案例和风险案例。
- `Page 8: Report Export`：导出 summary、metrics 和 risk-label 文件。

更多发表规划见：

- `README_EN.md`
- `docs/literature_publication_strategy.md`
- `docs/emnlp_demo_brief.md`
- `docs/casebook.md`
- `docs/demo_video_script.md`
- `docs/ethics_limitations.md`
- `docs/public_release_notes.md`
- `docs/release_checklist.md`
- `paper/consensusscope_emnlp_demo.tex`

生成英文系统截图：

```bash
node scripts/capture_screenshots_en.mjs
```

生成英文本地演示视频草稿，并转为 MP4：

```bash
node scripts/record_demo_video_en.mjs
python3 scripts/convert_video_to_mp4.py
```

Mac 下可直接双击：

```text
start_demo_mac.command
```

Windows 下可直接双击：

```text
start_demo.bat
```

## 测试

```bash
python3 -m compileall -q src scripts app tests
python3 -m pytest -q
```

全新环境测试：

```bash
python3 -m venv .venv-clean
source .venv-clean/bin/activate
pip install -U pip
pip install -r requirements.txt
python3 -m pytest -q
```

## 当前状态

本版本包含可导入的数据结构、配置读取、OpenAI 兼容客户端、JSON 答案解析、断点续跑、多数投票、固定裁决器、动态裁决、风险标注、指标计算、图表生成、Markdown 报告和 Streamlit 原型入口。
