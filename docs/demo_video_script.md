# ConsensusScope 2.5-Minute Demo Video Script

Target length: 2 minutes 30 seconds.

Important: the English narration below keeps the first-version audio script.
Do not re-record the narration unless the paper claim changes again. The
Chinese screen-operation notes are updated to match the current website.

## Recording Setup

- Open the live demo: `https://demo.consensusscope.cn/`
- Use the English UI.
- Do not show real API keys, service credentials, or private student data.
- Use the built-in synthetic demo records only.
- Keep the browser at roughly `1440 x 900` or full screen.
- If the site asks for a demo password, unlock it before starting the final
  recording.

## 0:00-0:20 Problem

Screen operation:

- 打开 `Page 1: Review Workspace`。
- 鼠标停在标题和顶部指标附近。
- 指一下主流程：single essay, batch review, comparison, queue, evaluation,
  reports。

Narration:

> AI writing feedback can be fluent but unsafe. A model may fix a local grammar
> issue while also changing a student's intended meaning, adding unsupported
> content, or overcorrecting a reasonable ESL draft.

## 0:20-0:50 Single Essay Review

Screen operation:

- 点击 `Page 2: Single Essay Review`。
- 选择内置 demo essay。
- 展示 assignment prompt、essay text、reviewer settings。
- 如果页面已有 routed feedback，就直接展示；如果没有，点击生成/路由按钮。
- 指向 auto-accepted items、teacher-review items、risk score、evidence signal、
  review explanation。

Narration:

> In the single essay window, a teacher can paste an ESL draft, provide the
> assignment prompt, and generate AI-style feedback candidates. The system then
> routes each feedback item before it reaches the student. Each item receives a
> risk score, evidence signal, review priority, and short explanation for the
> teacher.

## 0:50-1:10 Batch Review

Screen operation:

- 点击 `Page 3: Batch Review`。
- 展示 packaged synthetic CSV / sample data。
- 展示 batch summary table 和 routed feedback export。
- 不需要上传真实文件。

Narration:

> The batch window supports the practical classroom workflow: multiple essays
> can be processed from a CSV, then exported as routed feedback for teacher
> triage.

## 1:10-1:30 AI Feedback Comparison

Screen operation:

- 点击 `Page 4: AI Feedback Comparison`。
- 指向按 target span 和 issue type 对齐的反馈。
- 指向 risk level / consensus state / review routing 相关列。

Narration:

> The comparison page makes model disagreement visible. Feedback is grouped by
> target span and issue type, with reviewers, suggestions, risk levels, and
> consensus state shown together.

## 1:30-2:00 Teacher Queue And Cases

Screen operation:

- 点击 `Page 5: Teacher Queue`。
- 停在一个 high-risk item 上，例如 meaning change 或 unsupported claim。
- 指向 Feedback Safety Graph path、review confidence、evidence signal、
  priority、explanation。
- 如果页面有 action 控件，可以选择或展示一个 teacher action。

Narration:

> The teacher queue prioritizes high-risk feedback first. Here are four cases:
> a safe local phrase edit can be accepted; a thesis-reversing suggestion is
> routed to review; an unsupported exam-score claim is blocked; and a
> teacher-dependent punctuation suggestion is now reviewable after our
> two-teacher diagnostic pilot.

## 2:00-2:20 Effectiveness And Reports

Screen operation:

- 点击 `Page 6: Effectiveness Evaluation`。
- 指向 action accuracy、risk accuracy、high-risk recall、review recall、
  auto-accept precision。
- 如页面有公开学习者语料 benchmark 表，指向 auto share、review share、
  errors reviewed。
- 点击 `Page 7: Reports`，展示 report preview 和 export buttons。

Narration:

> The evaluation page separates two kinds of evidence. The synthetic checks
> verify implementation behavior, while the public learner-corpus benchmark
> evaluates routing on JFLEG, CoNLL-2014, FCE, and W&I plus LOCNESS correction
> data. We also ran a small two-teacher blind Likert pilot over 30 feedback
> items. After adding deploy-time signals for teacher-dependent wording,
> semantic drift, and wrong local corrections, review-needed and unsafe-item
> recall both reach 1.000. These results validate graph-backed review routing,
> not classroom learning outcomes.

## 2:20-2:30 Closing

Screen operation:

- 停在 Reports 或返回 Page 1。
- 鼠标不要动，留 1 秒安静收尾。

Narration:

> ConsensusScope turns AI writing feedback into a teacher-review workflow:
> generate, compare, route, review, and export.

## Do Not Say

- Do not say the system replaces teachers.
- Do not say the system proves classroom learning gains.
- Do not say the demo uses real student data.
- Do not mention API keys or backend secrets.
- Do not bring back the learned meta-judge claim.
