# ConsensusScope ESL UI 设计预设稿

本文件用于直接交付给中文 UI/UX 设计师。目标不是让设计师复刻当前 Streamlit 页面，而是把 ConsensusScope 重新包装成一个更像真实应用的 **英语二语比较文学论文反馈审阅系统**。

## 1. 产品定位

ConsensusScope 应该被设计成：

> 面向英语二语教学场景的 AI 写作反馈审阅与人工复核路由工作台。

用户打开系统后，第一眼看到的核心问题应是：

> 这条 AI 反馈能不能直接给学生？如果不能，为什么要交给教师复核？

不要把第一印象做成“多模型 QA 实验看板”或“算法指标展示页”。模型、投票、裁决算法可以存在，但应该服务于教师审阅流程。

## 2. 需要增强的界面

### P0：必须增强

1. **Teacher Review Workspace / 教师审阅工作台**
   - 作为第一主界面。
   - 展示学生原文、AI 反馈建议、系统裁决、风险原因、知识证据和教师操作。
   - 教师动作应清晰：Accept、Edit、Send to Review、Reject。

2. **Essay Feedback Review / 作文反馈审阅**
   - 强化“比较文学论文纠错/反馈”的任务感。
   - 输入区应像真实教师工具，而不是普通问答框。
   - 输出统一为 feedback item：issue type、suggestion、rationale、knowledge support、risk level、recommended action。

3. **Knowledge Evidence / 专家知识证据**
   - 重点展示知识图谱或专家知识库返回的证据。
   - 证据卡片应包含 entity、relation、source、confidence/usefulness。
   - 视觉上要让人相信系统不是凭空判断，而是在检查文学知识、人物、作品、体裁、年代、主题等信息。

4. **Teacher Review Queue / 人工复核队列**
   - 应该像真实工作台的待办列表。
   - 每条记录显示 priority、student excerpt、risk reason、knowledge gap、suggested action。
   - 让 reviewer 感觉系统解决的是“哪些反馈需要我看”的实际问题。

5. **Report Export / 报告导出**
   - 增强为可提交/可留档的教师审阅报告。
   - 应包括：case summary、accepted feedback、teacher-review items、knowledge evidence、audit trail、limitations。

### P1：保留但简化

1. **Risk Dashboard**
   - 保留，但从“算法性能看板”改成“复核负载和风险分布看板”。
   - 重点指标：auto-accept share、teacher-review share、high-risk feedback share、evidence-supported share。

2. **Model Reliability Dashboard**
   - 保留为后台分析页。
   - 只显示对教学审阅有帮助的模型行为：agreement、parse error、knowledge conflict、historical reliability。

3. **Adjudication Comparison**
   - 保留为 Advanced / Method Diagnostics。
   - 不要放在主导航前半段。
   - 避免让评审以为系统核心只是比较 majority vote、fixed judge、rule-based dynamic adjudication。

## 3. 需要弱化或隐藏的界面

1. **Auxiliary QA Live Comparison**
   - 弱化为 Advanced 里的辅助模块。
   - 不应出现在主线演示路径中。

2. **Auxiliary QA Case Explorer / Sample Audit**
   - 弱化为 legacy / auxiliary diagnostics。
   - 如果保留，页面标题必须说明它不是 ESL 主任务。

3. **API Configuration**
   - 不要长期占据主侧边栏。
   - 建议放入 Settings 弹窗或 Advanced Setup。
   - 演示版默认使用 sample records，避免让评审先看到 API key 配置。

4. **Raw Suggestions / Raw Model Trace**
   - 放到折叠区域。
   - 普通教师用户不需要一开始看到原始 JSON 或模型 trace。

5. **Majority Vote / Fixed Judge / Dynamic Judge 作为主标题**
   - 方法可以存在，但主页面标题应使用用户任务语言：
     - Feedback Safety
     - Teacher Review Routing
     - Knowledge Support
     - Risk Reason

## 4. 建议信息架构

主导航建议重排为：

1. **Review Workspace**
   - 首屏主工作台。
   - 汇总当前班级/样本的反馈审阅状态。

2. **Essay Review**
   - 单篇作文或片段审阅。
   - 输入作文、查看 AI 反馈、运行知识校验和裁决。

3. **Knowledge Evidence**
   - 展示知识图谱/专家知识库证据。
   - 按 author、work、character、theme、genre、period 等维度组织。

4. **Teacher Queue**
   - 人工复核队列。
   - 支持按 priority、risk level、issue type、evidence status 过滤。

5. **Risk & Routing Dashboard**
   - 展示系统节省多少人工审阅、哪些风险被拦截。

6. **Report Export**
   - 导出教师审阅报告、系统审计记录和演示材料。

7. **Advanced**
   - API Settings
   - Method Diagnostics
   - Auxiliary QA Reliability
   - Raw Data Inspector

## 5. 首屏预设布局

首屏建议使用“教师审阅工作台”布局：

- 左侧：垂直导航。
- 顶部：项目名、任务说明、demo/sample 状态、导出按钮。
- 主区域上方：4 个核心指标卡。
  - Auto-accepted feedback
  - Sent to teacher review
  - Knowledge-supported items
  - High-risk warnings
- 主区域左栏：学生原文和 AI 反馈预览。
- 主区域右栏：Teacher Review Queue。
- 下方：Knowledge Evidence 和 Validation Snapshot。

设计重点：

- 页面应该像一个可以被教师实际使用的工作台。
- 避免大面积营销风 hero。
- 避免单一蓝紫色调。
- 表格、卡片和按钮要紧凑，适合反复审阅。

## 6. 核心组件说明

### Feedback Item Card

字段建议：

- Issue Type: grammar / coherence / literary fact / interpretation / citation / style
- Suggested Feedback
- Rationale
- Knowledge Support
- Risk Level
- Recommended Action
- Teacher Action

### Risk Chip

颜色建议：

- Low: green
- Medium: amber
- High: red
- Needs Evidence: blue-gray

### Knowledge Evidence Card

字段建议：

- Entity
- Relation
- Evidence
- Source
- Match status
- Used for decision: yes/no

### Teacher Queue Row

字段建议：

- Priority
- Excerpt
- Issue Type
- Risk Reason
- Evidence Status
- Recommended Action

## 7. 当前没有数据时的占位策略

没有真实课堂数据或用户研究时，不要假装已有。界面可以预留：

- Teacher annotation set: reserved
- Classroom deployment study: planned
- LMS integration: reserved
- Real student identifiers: anonymized / not included
- Video demo URL: to be added after recording

这些占位可以增强诚实性，不会削弱系统感。

## 8. 给设计师的视觉方向

关键词：

- 教师工作台
- 审阅队列
- 知识证据
- 风险路由
- 可导出审计报告

风格建议：

- Quiet operational SaaS。
- 信息密度中高，但不要拥挤。
- 主色建议使用深墨蓝、白色、浅灰、绿色、琥珀色、红色作为功能色。
- 卡片圆角不超过 8px。
- 不要做大面积渐变、发光球、装饰性插画。
- 英文 UI 文案优先，因为面向国际会议演示。
- 中文可用于内部设计批注和交付说明。

## 9. 设计师应重点输出的稿件

建议设计师优先做 4 张高保真图：

1. Review Workspace 首屏。
2. Essay Review 单篇反馈审阅页。
3. Teacher Queue + Knowledge Evidence 复核队列页。
4. Report Export 报告导出页。

之后再做 Advanced 页面，不要先做模型指标页。

