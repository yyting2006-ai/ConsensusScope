# 多大模型协同决策可靠性研究与发表路线

更新日期：2026-05-31

## 1. 推荐总定位

本项目不要被写成“多模型投票是否提升准确率”的普通实验。更强的定位是：

> 多模型一致不等于可信。本项目研究多大模型协同决策中的风险状态识别，并把一致性、证据支持、少数派价值和答案漂移转化为可解释的动态裁决策略。

对应英文题目可以是：

> When Multi-LLM Consensus Fails: Risk-Aware Evaluation and Dynamic Adjudication for Collaborative LLM Decision-Making

## 2. 相关研究方向、局限与本项目切入点

| 方向 | 代表研究 | 已有贡献 | 局限 | 我们能做的事情 |
|---|---|---|---|---|
| 多智能体辩论 | Multi-Agent Debate Improves Reasoning via Communication, NeurIPS 2023 | 证明多个LLM通过交流可提升推理任务表现 | 重点在性能提升，较少解释什么时候讨论会带偏或形成共同错误 | 把讨论前后答案变化作为答案漂移率，识别讨论带偏样本 |
| 多模型共识/圆桌协商 | ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs, 2023 | 让多个模型通过共识提升推理结果 | 共识常被视为正向信号，缺少虚假共识诊断 | 区分真实共识与虚假共识，统计共同错误率 |
| 投票、自一致性 | Self-Consistency Improves Chain of Thought Reasoning in Language Models, ICLR 2023 | 通过多次采样和投票提升CoT推理 | 投票只看答案频率，不解释多数派是否可靠 | 对多数派答案加证据支持、置信错配和少数派预警 |
| LLM-as-a-Judge | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena, NeurIPS 2023 | 将强模型作为自动评审器，降低人工评测成本 | judge存在位置偏差、模型偏好、解释表面化等问题 | 不把裁决器当真理，而是把裁决器作为一个可比较基线 |
| 评审团式评估 | Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models, 2024 | 用多个模型组成评审团，降低单一judge偏差 | 仍偏向“谁赢”的评估，较少输出风险状态 | 输出“直接采纳、风险共识、反证分析、人工复核”等状态 |
| 不确定性与置信校准 | Can LLMs Express Their Uncertainty in Words?, 2024等 | 研究模型口头置信是否反映真实不确定性 | 主要围绕单模型校准，较少研究多模型置信错配 | 统计高置信错误、模型间置信分歧、置信-正确性错配 |
| 事实核查/证据支持 | FEVER等事实验证任务 | 有标准标签和证据，可测事实性 | 许多LLM协同实验只看最终答案，不看证据质量 | 把证据支持度纳入动态裁决，形成可复现评估协议 |

参考入口：

- Multi-Agent Debate Improves Reasoning via Communication: https://arxiv.org/abs/2305.14325
- ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs: https://arxiv.org/abs/2309.13007
- Self-Consistency Improves Chain of Thought Reasoning in Language Models: https://arxiv.org/abs/2203.11171
- Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena: https://arxiv.org/abs/2306.05685
- Replacing Judges with Juries: https://arxiv.org/abs/2404.18796
- FEVER: a large-scale dataset for Fact Extraction and VERification: https://aclanthology.org/N18-1074/

## 3. 建议拆成三个成果

### 成果A：核心方法论文

目标：ACL/EMNLP/EACL Findings、COLING、AAAI/IJCAI workshop，或作为期刊主文。

核心问题：

> 多模型协同中的一致性、分歧、少数派答案、证据支持和置信表达，能否预测最终裁决风险？

最低实验：

- 数据集：TruthfulQA、FEVER、CommonsenseQA，后续可加MMLU子集、HotpotQA或教育写作样本。
- 模型：DeepSeek、Qwen、GLM、Kimi，最好再加一个闭源强模型和一个开源本地模型。
- 协议：单模型、简单多数投票、固定judge、多模型讨论、动态裁决。
- 指标：Accuracy、Macro-F1、false consensus rate、minority-correct rate、answer drift rate、confidence mismatch rate、risk-level error rate、AUC for risk prediction。

### 成果B：系统Demo论文

目标：EMNLP 2026 System Demonstration 或其他ACL系demo/workshop。

系统名建议：ConsensusScope。

卖点：

- 可导入多模型回答trace；
- 展示一致率、分歧、少数派、证据缺口和风险标签；
- 对比多数投票、固定judge和动态裁决；
- 导出可复现CSV和Markdown报告；
- 服务事实核查、教育写作审核和LLM产品安全评估。

### 成果C：教育应用论文

目标：AIED、LAK、EDM、International Journal of Artificial Intelligence in Education、Computer Assisted Language Learning等。

问题：

> 多智能体审核反馈能否提高留学生比较文学论文的事实准确性、文本证据、比较逻辑、文化理解和学术写作质量？

关键要求：

- 学生文本匿名化；
- 人工评分rubric；
- 至少两名人工评分员，报告一致性；
- 初稿-二稿对照；
- AI审核报告的有效性和误导风险都要分析。

## 4. EMNLP Demo具体要求

根据EMNLP 2026 System Demonstrations官方页面，当前要点如下：

- 论文长度：最多6页，不含参考文献；可有无限制附录，但审稿人不一定阅读。
- 截止时间：2026-07-10，使用OpenReview提交。
- 演示视频：不超过2.5分钟；提交时必须提供video demonstration URL。
- 必须提供技术细节、截图、目标用户、评估、许可证。
- 没有任何评估的系统论文可能被desk reject。
- 最终录用论文需提交到ACL Rolling Review并转投EMNLP Demo会场。
- 录用后至少一名作者需要到会展示；如果必须远程展示，需要组织方批准。

官方页面：

- EMNLP 2026 System Demonstrations: https://2026.emnlp.org/calls/demos/
- EMNLP 2026 Main Conference Papers: https://2026.emnlp.org/calls/main_conference_papers/
- ACL Rolling Review dates: https://aclrollingreview.org/dates

## 5. 当前Demo系统还要补什么

已具备：

- Streamlit原型；
- 公开数据集统一样本；
- 多模型输出表；
- 多数投票、动态裁决、固定裁决器结果；
- 1000条风险标签；
- 方法指标、风险有效性、图表和实验报告；
- pytest测试。

需要补强：

- 英文README、LICENSE、匿名仓库；
- 2.5分钟demo视频；
- 系统截图和用户流程图；
- 典型案例页：虚假共识、少数派正确、高分歧、置信错配各2-3个；
- 可一键运行的小样本包，避免审稿人必须调用API；
- 伦理说明：系统只做风险提示，不替代事实核查或教师评分。

## 6. 二区及以上期刊建议

分区每年会变，正式投稿前需要用当年中科院分区表/JCR/Scimago再核验。按项目匹配度和可发表性，推荐顺序如下：

| 推荐顺序 | 期刊 | 推荐理由 | 难度 | 最适合的论文形态 |
|---|---|---|---|---|
| 1 | Expert Systems with Applications | 接受AI决策支持、专家系统、应用型可靠性评估；项目系统性强，较适配 | 中高 | 方法+系统+多数据集实验 |
| 2 | Knowledge-Based Systems | 适合知识驱动决策、可解释规则、评估框架 | 高 | 强调证据支持、风险规则和知识化裁决 |
| 3 | Information Processing & Management | 适合信息可靠性、事实核查、检索增强问答 | 高 | 强化FEVER和证据匹配 |
| 4 | Natural Language Engineering | 适合NLP工程系统、工具、资源和评估协议 | 中 | Demo系统+复现实验+错误分析 |
| 5 | Applied Soft Computing / Engineering Applications of Artificial Intelligence | 可投应用AI与决策框架 | 中高 | 动态裁决算法与机器学习风险预测 |
| 6 | International Journal of Artificial Intelligence in Education | 教育应用线适配 | 中高 | 学生写作审核实验，不建议和主技术文混投 |
| 7 | Computers and Education: Artificial Intelligence | 教育AI应用更友好 | 中 | AI审核反馈、学习效果、教师辅助评价 |

不建议优先投：

- 只偏理论机器学习的期刊：当前方法还不够理论化；
- 只收纯NLP模型创新的期刊：项目没有训练新模型；
- 纯教育期刊作为主技术文：会弱化多LLM可靠性贡献。

## 7. 最现实的时间表

| 时间 | 目标 |
|---|---|
| 2026-06-01至2026-06-20 | 完成Demo英文README、系统截图、典型案例库、伦理说明 |
| 2026-06-21至2026-07-05 | 写EMNLP Demo 6页论文，录2.5分钟视频 |
| 2026-07-10 | 投EMNLP 2026 System Demonstrations |
| 2026-07至2026-09 | 扩大数据、补讨论协议、补消融实验和跨模型泛化 |
| 2026-10 | 准备ACL ARR或期刊主文初稿 |
| 2026-11至2027-02 | 教育应用实验独立推进，形成第二篇论文 |

