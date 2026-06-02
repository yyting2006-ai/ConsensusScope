# ConsensusScope：面向 ESL 写作反馈的教师复核路由系统

**ConsensusScope: An Interactive Review-Routing Tool for Safe AI Feedback on ESL Writing**

ConsensusScope 当前主线是 **teacher-in-the-loop review routing for safe
AI-generated ESL writing feedback**。系统帮助教师判断 AI 写作反馈是否可以安全展示给学生，还是需要教师先复核、编辑或拒绝。

它不是自动作文评分系统，不是教师替代品，也不是“真值判定器”。

## 核心用途

AI 写作反馈可能很流畅，但并不一定安全。模型可能正确修改局部语法错误，也可能改写学生原意、反转论点、加入无依据内容，或把本来合理的表达过度纠正。ConsensusScope 的作用是把这些风险显性化：

- 多模型反馈统一成同一反馈格式；
- 使用部署时可获得的风险信号：模型一致性、issue type、meaning-change warning、unsupported-claim warning、parse error 等；
- 将反馈路由为 low / medium / high risk；
- 生成教师复核队列；
- 提供 Writing Rubric 和 Reports 页面，方便教师检查和导出审计记录。

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
streamlit run app/streamlit_app.py --server.port 8502
```

然后打开：

```text
http://localhost:8502
```

## 当前主线资产

- `app/streamlit_app.py`：可运行的教师工作台，包含单篇、批量、比对、队列、评估和报告窗口。
- `ui_prototype/index.html`：给设计师看的完整视觉原型。
- `profiles/esl_writing.yaml`：ESL 写作反馈 profile。
- `data/esl_writing_demo/`：合成 ESL 作文、反馈项、review evidence 和 routing output。
- `src/esl_writing_feedback.py`：规则型教师复核路由接口。
- `src/prompts/esl_feedback_prompt.py`：ESL feedback 生成 prompt 模板。
- `scripts/evaluate_esl_routing_demo.py`：合成期望标签上的路由有效性评估脚本。
- `scripts/analyze_esl_feedback_experiment.py`：未来导入真实教师标注后的离线分析脚本。

## 主线页面

1. Review Workspace
2. Single Essay Review：教师粘贴单篇作文，生成并路由 AI 反馈。
3. Batch Review：上传或使用 CSV 批量处理多篇作文。
4. AI Feedback Comparison：比较不同 AI reviewer 的反馈候选、风险和一致性状态。
5. Teacher Queue：教师复核、接受、编辑、拒绝或要求更多证据。
6. Effectiveness Evaluation：在合成期望标签上评估路由行为。
7. Reports：导出反馈表和教师可读报告。
8. Settings / Diagnostics：API 设置和旧辅助诊断。
9. Design Reference：设计师视觉参考。

核心工作流：

```text
Single Essay Review -> Batch Review -> AI Feedback Comparison -> Teacher Queue -> Effectiveness Evaluation -> Reports
```

## 数据边界

当前 ESL writing demo 使用 3 篇合成匿名作文和 15 条合成反馈项，只用于产品演示和接口对齐，不是课堂实验结果。

## 当前有效性评估

当前评估属于 **synthetic sanity check**：它检验系统路由规则在 15 条人工设定的合成期望标签上是否按预期工作。

```bash
PYTHONPATH=. python3 scripts/evaluate_esl_routing_demo.py
```

当前结果：

| 指标 | 数值 |
|---|---:|
| Items | 15 |
| Action accuracy | 1.000 |
| Risk accuracy | 1.000 |
| High-risk recall | 1.000 |
| Review recall | 1.000 |
| Auto-accept precision | 1.000 |

这说明 demo 路由逻辑在合成测试集上按设计运行；它还不能证明真实课堂有效性、教师满意度、学生学习提升或真实 LLM 反馈质量。投稿前如果要增强实证说服力，需要收集教师标注或真实匿名作文数据。

后续如加入真实学生作文，必须先删除姓名、学号、邮箱、学校标识、人口统计信息和任何可识别个人身份的信息。

## Legacy 说明

仓库中早期比较文学反馈与 QA reliability 文件仅作为 legacy / auxiliary material 保留，不再是当前 EMNLP 2026 demo 的主线 claim。

## License

MIT License。详见 `LICENSE`。
