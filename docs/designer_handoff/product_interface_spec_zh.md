# ConsensusScope 产品接口与页面规格

版本：v1 designer handoff  
用途：给 UI/UX 设计师、前端工程师、后端工程师统一产品边界。  
重要说明：当前 Streamlit 站点不作为最终 UI 方向，只作为技术 demo。

## 1. 产品一句话

ConsensusScope 是一个用于英语二语比较文学论文的 AI 反馈审阅系统。它将多模型生成的写作反馈与文学知识库证据进行对照，把低风险语言修改自动放行，把事实、人物关系、主题理解和论点变化等高风险反馈送入教师复核队列。

## 2. 用户任务

教师打开系统后，主要完成四件事：

1. 查看学生论文片段和 AI 生成反馈。
2. 判断哪些反馈可以直接给学生。
3. 审查系统标记的高风险反馈及其知识证据。
4. 导出可留档的反馈审阅报告。

系统不做：

- 不给学生自动打分；
- 不替代教师判断；
- 不声称所有文学解释都有唯一标准答案；
- 不把模型一致性等同于正确性。

## 3. 前后端接口边界

### 前端负责

- 页面布局、导航、状态展示；
- 作文输入、样例选择、筛选、排序；
- 教师动作：accept、edit、send_to_review、reject；
- 风险和证据的可视化；
- 报告预览与下载入口。

### 后端负责

- 保存 review session；
- 调用或读取多模型反馈；
- 检索文学知识库；
- 运行 adjudication / routing；
- 生成 feedback item、risk reason、knowledge evidence；
- 保存教师动作；
- 生成报告。

### 不在前端暴露

- 真实 API key；
- provider secrets；
- 原始系统 prompt；
- 完整模型 raw response；
- gold labels；
- offline diagnostic labels 的内部计算逻辑。

## 4. 固定页面结构

### Page A：Review Workspace

用途：系统首页，展示当前班级或样例集的审阅状态。

关键模块：

- Routing Summary
  - total feedback items
  - auto-accepted
  - teacher-review queue
  - high-risk warnings
  - knowledge-supported items
- Priority Queue Preview
- Recent Essay Sessions
- Export / Share actions

设计重点：

- 像教师工作台，不像论文实验页。
- 第一屏要看到“待复核”和“为什么复核”。

### Page B：Essay Review

用途：单篇作文或片段审阅。

关键模块：

- Essay input / sample selector
- Assignment context
- Run review
- Auto-accepted preview
- Feedback item list
- Teacher actions

主要字段：

- essay_text
- assignment_type
- feedback_items
- risk_level
- recommended_action
- evidence_status

### Page C：Feedback Detail

用途：查看一条反馈为什么被放行或送审。

关键模块：

- Original span
- Suggested feedback
- Reviewer agreement
- Knowledge evidence
- Risk reasons
- Teacher decision history

设计重点：

- 不要把模型 trace 放在最显眼位置。
- 先解释“教师为什么要看”，再展示模型细节。

### Page D：Teacher Queue

用途：人工复核任务列表。

关键模块：

- queue table
- filters
- priority chips
- bulk actions
- case detail drawer

推荐筛选项：

- risk_level
- issue_type
- evidence_status
- recommended_action
- status

### Page E：Knowledge Base

用途：展示系统用于校验的文学知识。

关键模块：

- search
- entity profile
- triple list
- evidence source
- coverage summary

实体类型：

- work
- author
- character
- theme
- genre
- period

### Page F：Reports

用途：生成教师审阅报告。

报告内容：

- accepted feedback
- teacher-review items
- knowledge evidence
- teacher actions
- limitations
- audit timestamp

### Page G：Settings

用途：技术配置和高级诊断。

内容：

- API mode
- provider configuration
- data source
- method diagnostics
- raw trace inspector
- auxiliary QA module

注意：Settings 不应是新用户看到的第一屏。

## 5. 核心数据对象

### ReviewSession

表示一次作文审阅任务。

关键字段：

- session_id
- essay
- status
- created_at
- review_mode
- routing_summary
- feedback_items

### FeedbackItem

表示一条可审阅的 AI 反馈。

关键字段：

- item_id
- span
- issue_type
- suggestion
- rationale
- risk_level
- risk_reasons
- recommended_action
- knowledge_evidence
- consensus_summary
- status

### KnowledgeEvidence

表示知识库证据。

关键字段：

- evidence_id
- entity
- relation
- value
- source
- match_status
- used_for_decision

### TeacherAction

表示教师操作。

关键字段：

- action_id
- item_id
- action_type
- edited_feedback
- note
- actor
- created_at

## 6. 状态流

FeedbackItem 状态：

1. `generated`
2. `auto_accepted`
3. `needs_teacher_review`
4. `teacher_accepted`
5. `teacher_edited`
6. `teacher_rejected`
7. `exported`

ReviewSession 状态：

1. `draft`
2. `running`
3. `ready_for_review`
4. `partially_reviewed`
5. `reviewed`
6. `exported`

## 7. 风险显示规则

前端可以直接展示 deploy-time risk signals：

- agreement rate
- answer / feedback diversity
- confidence distribution
- evidence availability
- minority warning
- parse errors
- model historical reliability
- knowledge conflict
- meaning-change risk

前端不要在真实使用场景直接展示为系统已知事实：

- false consensus
- minority correct
- true consensus
- confidence mismatch with gold

这些只能在离线分析或论文实验说明中出现。

## 8. 设计风格约束

- 英文 UI，中文设计文档。
- 视觉方向：quiet operational SaaS。
- 主界面高信息密度，但不要拥挤。
- 不要做 marketing landing page。
- 不要把 API key 和模型列表放在首屏。
- 不要把 majority vote / fixed judge / dynamic judge 做成主导航。
- 不要大面积使用紫色渐变或装饰图。
- 卡片圆角建议 6-8px。
- 表格要适合教师快速扫描。

## 9. 给设计师的首要任务

请优先输出这 5 张 Figma 高保真页面：

1. Review Workspace
2. Essay Review
3. Feedback Detail
4. Teacher Queue
5. Reports

Knowledge Base 和 Settings 可以第二轮再做。

