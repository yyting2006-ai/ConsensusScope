# ConsensusScope：面向英语二语比较文学写作反馈的知识增强多模型裁决系统

ConsensusScope 当前定位为一个 **knowledge-grounded multi-LLM review-routing
tool**：它面向英语二语比较文学论文反馈，帮助教师判断哪些 AI 反馈可以低风险采纳，哪些反馈必须进入人工复核队列。

它不是自动作文评分系统，不是教师替代品，也不是所谓“真理判定器”。

## 核心用途

AI 写作反馈可能很流畅，但并不一定安全。模型可以正确修改局部语法错误，也可能错误改写作者、出版年份、人物关系或学生的文学解释。ConsensusScope 的作用是把这些风险显性化：

- 多个 reviewer 输出统一反馈格式；
- 检索 curated 文学知识图谱；
- 区分低风险 grammar/style 修改与高风险 literary fact / argument / interpretation 修改；
- 生成教师复核队列；
- 导出可审计报告。

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

## 当前 ESL 数据快照

| 项目 | 数值 |
|---|---:|
| 文学作品数 | 30 |
| KG triples | 319 |
| Benchmark essays | 30 |
| Adjudicated feedback decisions | 59 |
| Auto-accepted low-risk edits | 14 |
| Teacher-review decisions | 45 |
| High-risk decisions | 20 |
| KG-supported decisions | 23 |

这个 30-case benchmark 是 workflow validation，不是大规模课堂实验，也不是 SOTA essay scoring 结果。

## 页面说明

- Page 1: Home / System Overview
- Page 2: ESL Feedback Review
- Page 3: Knowledge Grounding & Teacher Queue
- Page 4: Adjudication Comparison
- Page 5: Risk Dashboard
- Page 6: Model Reliability Dashboard
- Page 7: Auxiliary QA Case Explorer
- Page 8: Report Export

旧的多模型 QA 可靠性文件仅作为辅助 reliability module / legacy artifact 保留，不能作为本次 EMNLP demo 的主线 claim。

## API Key 与隐私

API key 只能放在本地 `.env` 或 Streamlit Secrets 中，不能写进论文、README、源码或录屏。公开部署建议使用用户自带 key 的 Mode B。

如需加入真实学生作文，必须先删除姓名、学号、邮箱、学校标识、人口统计信息和任何可识别个人身份的信息。当前打包 demo 使用匿名化或合成样例。

## License

MIT License。详见 `LICENSE`。
