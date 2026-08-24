# ConsensusScope：基于反馈安全图谱的 ESL 写作反馈教师复核路由系统

**ConsensusScope: A Teacher-Controlled Safety Routing System for AI-Generated ESL Writing Feedback**

ConsensusScope 当前主线是 **teacher-in-the-loop review routing for safe
AI-generated ESL writing feedback**。系统的核心机制是 **反馈安全图谱
（Feedback Safety Graph）**：把学生原文片段、AI 建议、证据信号、被触发的安全维度和最终路由决策连起来，帮助教师判断 AI 写作反馈是否可以安全展示给学生，还是需要先复核、编辑或拒绝。

它不是自动作文评分系统，不是教师替代品，也不是“真值判定器”。

正式演示地址：<https://demo.consensusscope.cn/>；后端接口文档：
<https://api.consensusscope.cn/docs>。

## 核心用途

AI 写作反馈可能很流畅，但并不一定安全。模型可能正确修改局部语法错误，也可能改写学生原意、反转论点、加入无依据内容，或把本来合理的表达过度纠正。ConsensusScope 的作用不是给作文自动打分，而是把每条 AI 反馈变成可审计的安全图谱：

- 多模型反馈统一成同一反馈格式；
- 使用部署时可获得的图谱节点：目标片段、上下文、AI 建议、预测问题类型、证据信号、安全维度、路由决策；
- 标记图谱安全维度：局部语言修改、保留原意、内容依据、教学语气、反馈具体性、模型一致性；
- 将反馈路由为 low / medium / high risk；
- 导出安全图谱路径，例如 `target_span -> ai_suggestion -> meaning_preservation -> teacher_review`；
- 生成教师复核队列；
- 提供 Writing Rubric 和 Reports 页面，方便教师检查和导出审计记录。

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 7864
```

另开一个终端运行前端：

```bash
CONSENSUS_SCOPE_BACKEND_URL=http://127.0.0.1:7864 \
streamlit run app/streamlit_app.py --server.port 8502
```

然后打开：

```text
http://localhost:8502
```

## 当前主线资产

- `app/streamlit_app.py`：中英文教师工作台，包含注册登录、课程与作业、单篇/批量评审、教师队列、报告、个人历史和意见反馈。
- `backend/`：带账号鉴权的 FastAPI 服务，按用户隔离课程、作业、匿名作文、异步评审任务、教师决策、审计日志和产品反馈，并负责服务器端模型调用。
- `ui_prototype/index.html`：给设计师看的完整视觉原型。
- `profiles/esl_writing.yaml`：ESL 写作反馈 profile。
- `data/esl_writing_demo/`：合成 ESL 作文、反馈项、review evidence、routing output 和 AI 评审压力测试集。
- `src/esl_writing_feedback.py`：反馈安全图谱构建与规则型教师复核路由接口。
- `src/prompts/esl_feedback_prompt.py`：ESL feedback 生成 prompt 模板。
- `scripts/evaluate_esl_routing_demo.py`：合成期望标签上的路由有效性评估脚本。
- `scripts/run_public_gec_benchmark.py`：公开学习者纠错语料路由评测脚本，支持 JFLEG、`.m2` GEC 文件和 source/reference CSV。
- `reports/public_gec_summary_20260608.md`：公开语料聚合评测结果，不包含重新分发的原始语料文本。
- `scripts/analyze_esl_feedback_experiment.py`：未来导入真实教师标注后的离线分析脚本。

## 主线页面

1. Review Workspace
2. Courses and Assignments：建立课程与作业，保存单篇匿名作文或导入 CSV。
3. Single Essay Review：打开已保存作文或粘贴单篇作文，生成并路由 AI 反馈。
4. Batch Review：按作业、上传 CSV 或使用示例批量处理多篇作文。
5. Teacher Queue：逐条查看原文片段与 AI 建议，并接受、编辑、拒绝或要求更多证据。
6. Reports and Exports：导出教师审计报告、路由数据和学生版反馈。
7. My Account：修改资料和密码、导出账号数据、恢复历史或删除账号。
8. Product Feedback：提交问题、功能建议、易用性或输出质量反馈。

`Settings / Diagnostics` 仅向配置的管理员显示。

核心工作流：

```text
Course -> Assignment -> Single / Batch Review -> Teacher Queue -> Reports -> Personal History
```

## 数据边界

当前 ESL writing demo 使用 3 篇合成匿名作文、15 条合成反馈项和 16 条 AI 评审压力测试项，只用于产品演示、接口对齐和实现级测试，不是课堂实验结果。

## AI 评审输出

ESL 路由层现在会为每条 AI 反馈输出：

- `risk_level`：low / medium / high。
- `recommended_action`：auto_accept / teacher_review / needs_more_evidence / reject。
- `risk_score`：部署时可见信号计算出的风险分，不使用 gold label。
- `review_confidence`：对路由判断本身的置信度，不等于反馈内容一定正确。
- `evidence_signal`：supported / missing / conflict / none。
- `review_priority`：low / normal / high / urgent。
- `review_explanation`：给教师看的简短解释。
- `safety_graph_active_dimensions`：被触发的安全图谱维度。
- `safety_graph_active_signals`：触发这些维度的具体风险信号。
- `safety_graph_path`：从反馈项到路由决策的可读路径。
- `safety_graph_summary`：给教师看的图谱摘要。
- `safety_graph_nodes` / `safety_graph_edges`：用于审计和复现的 JSON 图谱记录。

当前 AI 评审重点拦截：改写学生立场、整篇代写、引入外部事实或统计、伤害性语气、低模型一致性、解析失败、过于模糊的反馈。

## 当前有效性评估

当前评估包含两部分：一是 **synthetic sanity check**，检验系统路由规则在 15 条人工设定的合成期望标签和 16 条 AI 评审压力测试项上是否按预期工作；二是公开学习者纠错语料上的离线路由评测。

```bash
PYTHONPATH=. python3 scripts/evaluate_esl_routing_demo.py
```

当前结果：

| 指标 | 数值 |
|---|---:|
| Items | 31 |
| Action accuracy | 1.000 |
| Risk accuracy | 1.000 |
| High-risk recall | 1.000 |
| Review recall | 1.000 |
| Auto-accept precision | 1.000 |

这说明 demo 路由逻辑在合成测试集上按设计运行；它还不能证明真实课堂有效性、教师满意度、学生学习提升或真实 LLM 反馈质量。投稿前如果要增强实证说服力，需要收集教师标注或真实匿名作文数据。

公开语料评测已覆盖 JFLEG、CoNLL-2014 官方测试标注、FCE 和 W&I+LOCNESS train/dev。结果汇总见：

```text
reports/public_gec_summary_20260608.md
```

这些结果验证的是“复核路由层”能否把构造出的错误/风险反馈送入教师复核队列，不表示真实 LLM 反馈质量达到 100%，也不表示已经完成课堂实验。

后续如加入真实学生作文，必须先删除姓名、学号、邮箱、学校标识、人口统计信息和任何可识别个人身份的信息。

## 账号与数据边界

账号密码使用 PBKDF2-HMAC-SHA256 哈希保存，登录令牌只保存 SHA-256
哈希；课程、作业、作文、评审记录、教师决策和意见反馈均按账号隔离。
用户可以导出个人数据、删除一条评审，或永久删除账号及其关联记录。

后端会保存用户提交的作文原文，直到用户主动删除或部署方执行数据保留
策略。系统会在保存或调用外部模型前检查常见姓名、邮箱、电话、学号和班级
标识，但该检查不能替代人工匿名化。因此只能上传匿名化作文；真实课堂部署
还需要遵守学校的数据处理、备份和保留制度。配置 SMTP 后可使用邮箱验证和
忘记密码链接；未配置邮件服务时需由部署管理员协助找回。

## 实时模型与密钥

默认评审器不调用外部 API，适合复现和体验完整流程。部署方也可以在后端
环境变量或密钥管理服务中配置 DeepSeek、Qwen、GLM、Kimi 或 OpenAI
兼容模型。访问者不需要、也不能在浏览器里输入模型 API key；密钥不会写入
评审记录、导出文件或健康检查响应。

当前 SQLite 配置适合单个 API 进程和产品试用。多实例或持续高并发部署前，
应迁移到托管关系型数据库，并建立加密备份、数据保留和监控策略。

## Legacy 说明

仓库中早期比较文学反馈与 QA reliability 文件仅作为 legacy / auxiliary material 保留，不再是当前 EMNLP 2026 demo 的主线 claim。

## License

MIT License。详见 `LICENSE`。
