# ConsensusScope 设计师交付包

这套文件用于交给中文 UI/UX 设计师。请注意：**当前 Streamlit 网站不作为最终参会 UI 方向**。它只证明后端流程、数据、知识库和裁决逻辑可以跑通。真正参会展示应重新设计为一个面向教师的英语二语写作反馈审阅产品。

## 设计目标

ConsensusScope 需要被包装成：

> 面向英语二语比较文学论文的 AI 反馈审阅、知识校验和人工复核路由系统。

核心用户不是算法研究员，而是：

- 英语二语写作教师；
- 教学技术产品经理；
- 教育 NLP 系统开发者；
- 需要审计 AI 写作反馈风险的研究者。

核心问题不是“哪个模型赢了”，而是：

> 这条 AI 反馈能不能直接给学生？如果不能，为什么需要教师复核？

## 设计师应该看的文件

1. `product_interface_spec_zh.md`
   - 产品定位、页面结构、前后端接口边界、设计约束。

2. `consensusscope_api_contract.yaml`
   - 固定下来的 v1 API 形态，供前端、后端和设计师统一字段。

3. `ui_state_models.json`
   - 反馈项、复核队列、报告导出的核心状态。

4. `site_reference.html`
   - 新网站参考原型。它不是最终视觉稿，而是给设计师理解信息架构、页面层级和交互重点。

5. `screenshots/site_reference_desktop.png`
   - `site_reference.html` 的桌面截图，便于微信或邮件快速预览。

## 当前旧网站如何处理

旧 Streamlit 网站只保留为技术 demo：

- 用于验证数据和算法；
- 用于跑 no-API 样例；
- 用于论文录屏中的技术证明；
- 不作为最终 UI 美术方向。

设计师不需要沿用旧网站的导航、配色、卡片样式或页面顺序。

## 新网站主导航建议

1. Review Workspace
2. Essay Review
3. Feedback Detail
4. Teacher Queue
5. Knowledge Base
6. Reports
7. Settings

需要弱化到 Settings / Advanced 的内容：

- API Configuration；
- raw model traces；
- majority vote / fixed judge / dynamic adjudication 的细节比较；
- auxiliary QA reliability；
- offline benchmark labels。

## 参会 UI 原则

- 最终 UI 应由人工设计师在 Figma 中重新完成。
- 参考网站只提供产品结构、信息优先级和字段样例。
- 论文和 demo 中不要展示真实 API key。
- 不要声称系统已经有大规模课堂验证。
- 不要把系统描述成自动评分器或教师替代品。

