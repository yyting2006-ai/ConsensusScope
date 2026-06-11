const pages = [
  { id: "workspace", label: "Page 1: Review Workspace" },
  { id: "review", label: "Page 2: Essay Review" },
  { id: "detail", label: "Page 3: Feedback Detail" },
  { id: "queue", label: "Page 4: Teacher Queue" },
  { id: "rubric", label: "Page 5: Writing Rubric" },
  { id: "reports", label: "Page 6: Reports" },
  { id: "settings", label: "Page 7: Settings / Diagnostics" },
];

const riskLabels = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

const statusLabels = {
  auto_accepted: "Auto accepted",
  needs_teacher_review: "Needs teacher review",
  teacher_accepted: "Teacher accepted",
  teacher_edited: "Teacher edited",
  teacher_rejected: "Teacher rejected",
};

const issueLabels = {
  all: "All issue types",
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  sentence_structure: "Sentence structure",
  coherence: "Coherence",
  organization: "Organization",
  task_response: "Task response",
  argument_clarity: "Argument clarity",
  tone_register: "Tone / register",
  meaning_change: "Meaning change",
  overcorrection: "Overcorrection",
};

const sessions = [
  {
    id: "ESL-WR-001",
    title: "Essay 01: Online learning in universities",
    assignmentPrompt: "Write an argumentative essay about whether online learning should remain part of university education.",
    essayGenre: "Argumentative essay",
    level: "Upper-intermediate ESL",
    wordCount: 78,
    draftStage: "First draft",
    status: "Ready for teacher review",
    riskSummary: "1 high-risk feedback item, 2 medium-risk items, 2 low-risk local edits",
    excerpt:
      "Online learning gives students more freedom because they can review lectures at home and save travel time. However, some students lose attention when the class is only online. I think universities should keep online learning, but teachers must make it more interactive. If online learning replaces all classroom learning, students may have fewer chances to discuss ideas face to face.",
  },
  {
    id: "ESL-WR-002",
    title: "Essay 02: Social media and teenagers",
    assignmentPrompt: "Write an opinion essay about how social media affects teenagers.",
    essayGenre: "Opinion essay",
    level: "Intermediate ESL",
    wordCount: 69,
    draftStage: "Revision draft",
    status: "Needs queue triage",
    riskSummary: "2 high-risk feedback items, 1 medium-risk item, 2 low-risk local edits",
    excerpt:
      "Social media helps teenagers communicate with friends and learn about the world. But it also make students compare their lives with others too much. In my opinion, social media is useful when teenagers control their time. Schools should teach students how to use it carefully instead of only saying it is bad.",
  },
  {
    id: "ESL-WR-003",
    title: "Essay 03: Environmental protection in cities",
    assignmentPrompt: "Write a problem-solution essay about environmental protection in cities.",
    essayGenre: "Problem-solution essay",
    level: "Upper-intermediate ESL",
    wordCount: 70,
    draftStage: "First draft",
    status: "In review",
    riskSummary: "1 high-risk feedback item, 1 medium-risk item, 3 low-risk local edits",
    excerpt:
      "Many cities face air pollution, plastic waste, and traffic problems. People know the environment is important, but they still choose convenient habits. The government should improve public transport and encourage recycling. Citizens also need to change small habits, such as bringing reusable bags and using less private cars.",
  },
];

const feedbackItems = [
  {
    id: "FW-001",
    sessionId: "ESL-WR-001",
    title: "Vocabulary edit for flexibility",
    issueType: "vocabulary",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "gives students more freedom",
    aiSuggestion: "Change to 'offers students greater flexibility'.",
    studentFacing: "Consider using 'offers students greater flexibility' for a more academic tone.",
    rationale: "Local vocabulary improvement that preserves the student's claim.",
    reason: "Local language edit; no stance or meaning change detected.",
    evidence: "Rubric: vocabulary precision; safety rule: meaning preserved.",
    group: "auto_accept",
    modelTrace: {
      agreement: "4 / 4 feedback generators agree this is local wording",
      signal: "No thesis or task-response change",
      action: "Auto accept",
    },
  },
  {
    id: "FW-002",
    sessionId: "ESL-WR-001",
    title: "Natural phrasing for attention",
    issueType: "vocabulary",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "lose attention",
    aiSuggestion: "Change to 'may lose focus'.",
    studentFacing: "Try 'may lose focus' for more natural academic phrasing.",
    rationale: "Natural phrasing improves clarity without adding a new idea.",
    reason: "Local vocabulary edit; rubric-supported.",
    evidence: "Rubric: vocabulary clarity.",
    group: "auto_accept",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Meaning-preservation risk is low",
      action: "Auto accept",
    },
  },
  {
    id: "FW-003",
    sessionId: "ESL-WR-001",
    title: "Thesis reversal risk",
    issueType: "meaning_change",
    risk: "high",
    status: "needs_teacher_review",
    originalSpan: "universities should keep online learning",
    aiSuggestion: "Rewrite the thesis to argue that universities should end online learning completely.",
    studentFacing: "Teacher review required before this feedback can be shown.",
    rationale: "The suggestion reverses the student's position.",
    reason: "Meaning-change risk: the feedback changes the student's thesis instead of improving expression.",
    evidence: "Safety rule: preserve student stance unless the teacher explicitly requests thesis revision.",
    group: "teacher_review",
    modelTrace: {
      agreement: "2 / 4 feedback generators flagged meaning-change risk",
      signal: "Teacher review required because the suggested revision changes stance",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-004",
    sessionId: "ESL-WR-001",
    title: "Argument detail request",
    issueType: "argument_clarity",
    risk: "medium",
    status: "needs_teacher_review",
    originalSpan: "make it more interactive",
    aiSuggestion: "Add a short explanation of interactive activities such as discussions or quizzes.",
    studentFacing: "Add one concrete example of how teachers can make online learning interactive.",
    rationale: "Specific examples can improve argument development.",
    reason: "Medium risk because the advice adds development content.",
    evidence: "Rubric: task response and argument clarity.",
    group: "teacher_review",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Development advice should be checked by a teacher",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-005",
    sessionId: "ESL-WR-001",
    title: "Organization change",
    issueType: "organization",
    risk: "medium",
    status: "needs_teacher_review",
    originalSpan: "fewer chances to discuss ideas face to face",
    aiSuggestion: "Move this sentence before the thesis to create a clearer contrast.",
    studentFacing: "Consider whether this counterpoint should appear earlier in the paragraph.",
    rationale: "The change affects paragraph organization.",
    reason: "Medium risk because structure changes may alter emphasis.",
    evidence: "Rubric: organization and coherence.",
    group: "teacher_review",
    modelTrace: {
      agreement: "2 / 4 feedback generators agree",
      signal: "Organization advice affects essay structure",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-006",
    sessionId: "ESL-WR-002",
    title: "Subject-verb agreement",
    issueType: "grammar",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "it also make students",
    aiSuggestion: "Change 'make' to 'makes'.",
    studentFacing: "Use 'makes' because the subject is singular.",
    rationale: "Subject-verb agreement correction.",
    reason: "Local grammar edit; meaning preserved.",
    evidence: "Rubric: grammar accuracy.",
    group: "auto_accept",
    modelTrace: {
      agreement: "4 / 4 feedback generators agree",
      signal: "Local correction only",
      action: "Auto accept",
    },
  },
  {
    id: "FW-007",
    sessionId: "ESL-WR-002",
    title: "Vocabulary precision",
    issueType: "vocabulary",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "compare their lives with others too much",
    aiSuggestion: "Change to 'compare themselves with others excessively'.",
    studentFacing: "Try 'compare themselves with others excessively' for a more formal style.",
    rationale: "Concise vocabulary improvement that preserves meaning.",
    reason: "Local vocabulary edit; no new claim.",
    evidence: "Rubric: vocabulary precision.",
    group: "auto_accept",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Meaning-preservation risk is low",
      action: "Auto accept",
    },
  },
  {
    id: "FW-008",
    sessionId: "ESL-WR-002",
    title: "Example request",
    issueType: "coherence",
    risk: "medium",
    status: "needs_teacher_review",
    originalSpan: "Schools should teach students",
    aiSuggestion: "Add evidence or an example of what schools can teach.",
    studentFacing: "Give one example of what schools can teach about careful social media use.",
    rationale: "A concrete example would make the paragraph more persuasive.",
    reason: "Medium risk because the student may need teacher guidance on development.",
    evidence: "Rubric: coherence and development.",
    group: "teacher_review",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Development advice requires teacher review",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-009",
    sessionId: "ESL-WR-002",
    title: "Overcorrection risk",
    issueType: "overcorrection",
    risk: "high",
    status: "needs_teacher_review",
    originalSpan: "instead of only saying it is bad",
    aiSuggestion: "Tell the student that social media is always harmful and should be banned.",
    studentFacing: "Teacher review required before this feedback can be shown.",
    rationale: "The suggestion overstates and changes the student's position.",
    reason: "Overcorrection and meaning-change risk.",
    evidence: "Safety rule: avoid replacing the student's stance with a stronger unsupported stance.",
    group: "teacher_review",
    modelTrace: {
      agreement: "2 / 4 feedback generators flagged high risk",
      signal: "Suggested feedback changes stance",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-010",
    sessionId: "ESL-WR-002",
    title: "Unsupported new claim",
    issueType: "task_response",
    risk: "high",
    status: "needs_teacher_review",
    originalSpan: "learn about the world",
    aiSuggestion: "Add a claim that social media improves teenagers' exam scores.",
    studentFacing: "Teacher review required before this feedback can be shown.",
    rationale: "The claim is not supported by the current draft.",
    reason: "Unsupported new argument.",
    evidence: "Safety rule: do not add claims absent from the draft or assignment.",
    group: "teacher_review",
    modelTrace: {
      agreement: "1 / 4 feedback generators support the suggestion",
      signal: "Low agreement and unsupported-claim warning",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-011",
    sessionId: "ESL-WR-003",
    title: "List punctuation",
    issueType: "grammar",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "air pollution, plastic waste, and traffic problems",
    aiSuggestion: "Keep comma use consistent in the list.",
    studentFacing: "Your list punctuation is clear; keep the comma pattern consistent.",
    rationale: "Punctuation/style edit with no meaning change.",
    reason: "Local grammar edit.",
    evidence: "Rubric: grammar and mechanics.",
    group: "auto_accept",
    modelTrace: {
      agreement: "4 / 4 feedback generators agree",
      signal: "Local correction only",
      action: "Auto accept",
    },
  },
  {
    id: "FW-012",
    sessionId: "ESL-WR-003",
    title: "Vocabulary clarity",
    issueType: "vocabulary",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "convenient habits",
    aiSuggestion: "Change to 'convenient but unsustainable habits'.",
    studentFacing: "Try 'convenient but unsustainable habits' to make the contrast clearer.",
    rationale: "The phrase improves precision without changing the intended meaning.",
    reason: "Local vocabulary edit; meaning preserved.",
    evidence: "Rubric: vocabulary precision.",
    group: "auto_accept",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Meaning-preservation risk is low",
      action: "Auto accept",
    },
  },
  {
    id: "FW-013",
    sessionId: "ESL-WR-003",
    title: "Countable noun correction",
    issueType: "grammar",
    risk: "low",
    status: "auto_accepted",
    originalSpan: "using less private cars",
    aiSuggestion: "Change to 'using fewer private cars'.",
    studentFacing: "Use 'fewer' with countable nouns: 'using fewer private cars'.",
    rationale: "Countable noun grammar correction.",
    reason: "Local grammar edit; meaning preserved.",
    evidence: "Rubric: grammar accuracy.",
    group: "auto_accept",
    modelTrace: {
      agreement: "4 / 4 feedback generators agree",
      signal: "Local correction only",
      action: "Auto accept",
    },
  },
  {
    id: "FW-014",
    sessionId: "ESL-WR-003",
    title: "Unsupported solution",
    issueType: "meaning_change",
    risk: "high",
    status: "needs_teacher_review",
    originalSpan: "The government should improve public transport",
    aiSuggestion: "Add a new argument that factories should be closed immediately.",
    studentFacing: "Teacher review required before this feedback can be shown.",
    rationale: "The feedback introduces a new unsupported argument.",
    reason: "Meaning-change and unsupported-claim risk.",
    evidence: "Safety rule: do not add policy claims that are absent from the draft.",
    group: "teacher_review",
    modelTrace: {
      agreement: "1 / 4 feedback generators support the suggestion",
      signal: "Unsupported new argument",
      action: "Route to teacher",
    },
  },
  {
    id: "FW-015",
    sessionId: "ESL-WR-003",
    title: "Coherence transition",
    issueType: "coherence",
    risk: "medium",
    status: "needs_teacher_review",
    originalSpan: "Citizens also need to change small habits",
    aiSuggestion: "Add a transition explaining how citizen actions complement government policies.",
    studentFacing: "Add a transition showing how personal actions connect to government policies.",
    rationale: "The suggestion improves coherence between proposed solutions.",
    reason: "Medium risk because development advice may shape argument flow.",
    evidence: "Rubric: coherence and organization.",
    group: "teacher_review",
    modelTrace: {
      agreement: "3 / 4 feedback generators agree",
      signal: "Development advice requires teacher review",
      action: "Route to teacher",
    },
  },
];

const rubricRows = [
  {
    dimension: "Meaning preservation",
    deploySignal: "Does the feedback preserve the student's stance, claim, and intended meaning?",
    reviewRule: "Route to teacher when the suggestion rewrites the thesis, adds a new claim, or changes the student's position.",
    example: "Changing 'keep online learning' to 'end online learning' is high risk.",
  },
  {
    dimension: "Local language edit",
    deploySignal: "Is the feedback limited to grammar, punctuation, or wording?",
    reviewRule: "Auto accept when meaning is preserved and model agreement is high.",
    example: "Changing 'make' to 'makes' is low risk.",
  },
  {
    dimension: "Task response",
    deploySignal: "Does the feedback ask for content that fits the assignment prompt?",
    reviewRule: "Route to teacher when the suggestion adds unsupported evidence or a new topic.",
    example: "Adding an exam-score claim to a social-media essay requires review.",
  },
  {
    dimension: "Organization and coherence",
    deploySignal: "Does the suggestion rearrange or extend the student's argument?",
    reviewRule: "Route to teacher when paragraph structure, emphasis, or development changes.",
    example: "Moving a counterargument before the thesis is medium risk.",
  },
  {
    dimension: "Tone and student safety",
    deploySignal: "Is the feedback supportive, specific, and non-punitive?",
    reviewRule: "Reject or rewrite harsh, vague, or discouraging feedback before release.",
    example: "A teacher edits vague feedback into one concrete next step.",
  },
];

const state = {
  page: "workspace",
  selectedSessionId: "ESL-WR-001",
  selectedFeedbackId: "FW-003",
  queueFilters: {
    risk: "all",
    issue: "all",
    status: "all",
  },
  savedDecision: null,
};

const viewRoot = document.getElementById("viewRoot");
const sideNav = document.getElementById("sideNav");
const toast = document.getElementById("toast");

function riskClass(risk) {
  return `risk-${risk}`;
}

function statusClass(status) {
  return {
    auto_accepted: "status-auto",
    needs_teacher_review: "status-review",
    teacher_edited: "status-edited",
    teacher_accepted: "status-auto",
    teacher_rejected: "status-rejected",
    exported: "status-exported",
  }[status] || "status-review";
}

function currentSession() {
  return sessions.find((session) => session.id === state.selectedSessionId) || sessions[0];
}

function sessionItems(sessionId = state.selectedSessionId) {
  return feedbackItems.filter((item) => item.sessionId === sessionId);
}

function selectedFeedback() {
  return feedbackItems.find((item) => item.id === state.selectedFeedbackId) || feedbackItems[0];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderNav() {
  sideNav.innerHTML = pages
    .map(
      (page) => `
        <button class="nav-button ${state.page === page.id ? "is-active" : ""}" data-page="${page.id}">
          ${page.label}
        </button>
      `
    )
    .join("");
}

function pageHeading(eyebrow, title, copy, actions = "") {
  return `
    <div class="page-heading">
      <div>
        <div class="eyebrow">${eyebrow}</div>
        <h1>${title}</h1>
        <p class="page-copy">${copy}</p>
      </div>
      ${actions ? `<div class="actions">${actions}</div>` : ""}
    </div>
  `;
}

function metricCard(label, value, note) {
  return `
    <div class="metric-card">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
      <div class="metric-note">${note}</div>
    </div>
  `;
}

function pill(label, className = "pill--neutral") {
  return `<span class="pill ${className}">${label}</span>`;
}

function riskBadge(risk) {
  return `<span class="risk-badge ${riskClass(risk)}">${riskLabels[risk]}</span>`;
}

function statusChip(status) {
  return `<span class="status-chip ${statusClass(status)}">${statusLabels[status] || status}</span>`;
}

function contextItem(label, value) {
  return `
    <div class="context-item">
      <div class="context-label">${label}</div>
      <div class="context-value">${escapeHtml(value)}</div>
    </div>
  `;
}

function renderSessionCard(session) {
  const items = sessionItems(session.id);
  const reviewCount = items.filter((item) => item.group === "teacher_review").length;
  const autoCount = items.filter((item) => item.group === "auto_accept").length;
  return `
    <div class="session-card">
      <div class="chip-row">
        ${pill(session.id, "pill--blue")}
        ${pill(session.draftStage)}
      </div>
      <div class="session-card__title">${session.title}</div>
      <div class="session-meta">${session.assignmentPrompt}</div>
      <div class="chip-row">
        ${pill(`${autoCount} auto accepted`)}
        ${pill(`${reviewCount} in teacher queue`)}
      </div>
      <button class="button primary" data-open-session="${session.id}">Open review</button>
    </div>
  `;
}

function renderFeedbackCard(item, compact = false) {
  const displayStatus = state.savedDecision && item.id === state.savedDecision.feedbackId ? state.savedDecision.status : item.status;
  return `
    <div class="feedback-item-card ${item.risk}">
      <div class="feedback-card-head">
        <div>
          <div class="feedback-card-title">${item.title}</div>
          <div class="feedback-card-copy">${escapeHtml(item.aiSuggestion)}</div>
        </div>
        <div class="chip-row">
          ${riskBadge(item.risk)}
          ${statusChip(displayStatus)}
        </div>
      </div>
      ${compact ? "" : `<div class="feedback-card-copy"><strong>Student-facing draft:</strong> ${escapeHtml(item.studentFacing)}</div>`}
      <div class="feedback-card-copy"><strong>Reason:</strong> ${escapeHtml(item.reason)}</div>
      <div class="teacher-action-toolbar">
        <button class="button secondary" data-open-feedback="${item.id}">Open detail</button>
        ${item.group === "teacher_review" ? `<button class="button" data-queue-feedback="${item.id}">Queue</button>` : ""}
      </div>
    </div>
  `;
}

function renderWorkspace() {
  const total = feedbackItems.length;
  const auto = feedbackItems.filter((item) => item.group === "auto_accept").length;
  const review = feedbackItems.filter((item) => item.group === "teacher_review").length;
  const high = feedbackItems.filter((item) => item.risk === "high").length;

  viewRoot.innerHTML = `
    ${pageHeading(
      "Review workspace",
      "Route AI writing feedback before it reaches students.",
      "ConsensusScope is a teacher-in-the-loop review workspace for ESL writing feedback. Each AI suggestion is represented as a Feedback Safety Graph linking the target span, suggestion, evidence signal, safety dimension, and route.",
      '<button class="button primary" data-open-session="ESL-WR-001">Start current review</button><button class="button secondary" data-page-jump="queue">Open teacher queue</button>'
    )}

    <div class="grid four">
      ${metricCard("Feedback items", total, "Synthetic ESL writing demo set")}
      ${metricCard("Auto accepted", auto, "Low-risk local edits")}
      ${metricCard("Teacher queue", review, "Medium/high-risk items")}
      ${metricCard("High risk", high, "Meaning-change or unsupported-claim warnings")}
    </div>

    <div class="routing-card">
      <strong>Primary workflow.</strong>
      Multi-model feedback candidates are normalized into one schema, converted into item-level Feedback Safety Graphs, then shown as either student-ready local edits or teacher-review items. The system supports teacher judgment; it does not replace grading or final feedback decisions.
    </div>

    <div class="grid three">
      ${sessions.map(renderSessionCard).join("")}
    </div>

    <div class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Deploy-time routing signals</div>
          <div class="panel-subtitle">Signals available before teacher annotation or offline evaluation.</div>
        </div>
      </div>
      <div class="panel-body">
        <div class="grid three">
          ${metricCard("Agreement", "model-level", "How many feedback generators support the item")}
          ${metricCard("Diversity", "suggestion-level", "Whether the item changes stance or adds content")}
          ${metricCard("Rubric match", "rule-level", "Grammar, vocabulary, coherence, task response, and safety checks")}
        </div>
      </div>
    </div>
  `;
}

function renderEssayReview() {
  const session = currentSession();
  const items = sessionItems(session.id);
  const auto = items.filter((item) => item.group === "auto_accept");
  const review = items.filter((item) => item.group === "teacher_review");

  viewRoot.innerHTML = `
    ${pageHeading(
      "Essay review",
      session.title,
      "Review one anonymized ESL writing draft, inspect routing decisions, and open high-risk feedback before it reaches the student.",
      '<button class="button secondary" data-page-jump="workspace">Back to workspace</button><button class="button primary" data-page-jump="queue">Open queue</button>'
    )}

    <div class="grid two">
      <div class="panel shadow">
        <div class="panel-header">
          <div>
            <div class="panel-title">Essay context</div>
            <div class="panel-subtitle">Synthetic anonymized draft for product demonstration.</div>
          </div>
          ${pill(session.id, "pill--blue")}
        </div>
        <div class="panel-body">
          <div class="essay-context">
            ${contextItem("Genre", session.essayGenre)}
            ${contextItem("Level", session.level)}
            ${contextItem("Draft", session.draftStage)}
          </div>
          <div style="height: 12px"></div>
          <div class="context-item">
            <div class="context-label">Assignment prompt</div>
            <div class="context-value">${escapeHtml(session.assignmentPrompt)}</div>
          </div>
          <div style="height: 12px"></div>
          <div class="essay-excerpt">${escapeHtml(session.excerpt)}</div>
        </div>
      </div>

      <div class="panel shadow">
        <div class="panel-header">
          <div>
            <div class="panel-title">Routing summary</div>
            <div class="panel-subtitle">Teachers see action distribution before inspecting individual feedback.</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="grid two">
            ${metricCard("Auto accepted", String(auto.length), "Low-risk local edits")}
            ${metricCard("Teacher review", String(review.length), "Medium/high-risk items")}
          </div>
          <div style="height: 12px"></div>
          <div class="routing-card">${session.riskSummary}</div>
        </div>
      </div>
    </div>

    <div>
      <div class="feedback-group-title">Auto accepted local edits</div>
      <div class="grid two">${auto.map((item) => renderFeedbackCard(item)).join("")}</div>
      <div class="feedback-group-title">Needs teacher review</div>
      <div class="grid two">${review.map((item) => renderFeedbackCard(item)).join("")}</div>
    </div>
  `;
}

function renderFeedbackDetail() {
  const item = selectedFeedback();
  const session = sessions.find((essay) => essay.id === item.sessionId) || currentSession();
  const displayStatus = state.savedDecision && item.id === state.savedDecision.feedbackId ? state.savedDecision.status : item.status;

  viewRoot.innerHTML = `
    ${pageHeading(
      "Feedback detail",
      item.title,
      "Inspect why an AI feedback item is safe to release, needs editing, or must remain in teacher review.",
      '<button class="button secondary" data-page-jump="review">Back to essay</button><button class="button primary" data-page-jump="queue">Open queue</button>'
    )}

    <div class="detail-layout">
      <div class="panel shadow">
        <div class="panel-header">
          <div>
            <div class="panel-title">Feedback item</div>
            <div class="panel-subtitle">${session.title}</div>
          </div>
          <div class="chip-row">
            ${riskBadge(item.risk)}
            ${statusChip(displayStatus)}
          </div>
        </div>
        <div class="panel-body">
          <div class="essay-context">
            ${contextItem("Issue type", issueLabels[item.issueType])}
            ${contextItem("Risk level", riskLabels[item.risk])}
            ${contextItem("Route", item.group === "auto_accept" ? "Auto accept" : "Teacher review")}
          </div>
          <div style="height: 12px"></div>
          <div class="context-item">
            <div class="context-label">Original span</div>
            <div class="context-value">${escapeHtml(item.originalSpan)}</div>
          </div>
          <div style="height: 12px"></div>
          <div class="context-item">
            <div class="context-label">AI suggestion</div>
            <div class="context-value">${escapeHtml(item.aiSuggestion)}</div>
          </div>
          <div style="height: 12px"></div>
          <div class="context-item">
            <div class="context-label">Student-facing draft</div>
            <div class="context-value">${escapeHtml(item.studentFacing)}</div>
          </div>
          <div style="height: 12px"></div>
          <div class="explain-box">
            <strong>Routing explanation.</strong>
            ${escapeHtml(item.reason)}
          </div>
          <div style="height: 12px"></div>
          <div class="teacher-action-toolbar">
            <button class="button" data-decision="teacher_accepted">Accept</button>
            <button class="button" data-edit-toggle>Edit</button>
            <button class="button danger" data-decision="teacher_rejected">Reject</button>
            <button class="button primary" id="saveDecisionButton">Save teacher decision</button>
          </div>
          <div class="edit-box" id="editBox">
            <label>
              Revised teacher feedback
              <textarea id="teacherEdit">${escapeHtml(item.studentFacing)}</textarea>
            </label>
          </div>
          <div class="success-message" id="successMessage">Decision saved in the local prototype state.</div>
        </div>
      </div>

      <div class="grid">
        <div class="detail-drawer">
          <div class="panel-title">Model and routing trace</div>
          ${contextItem("Agreement", item.modelTrace.agreement)}
          ${contextItem("Signal", item.modelTrace.signal)}
          ${contextItem("Action", item.modelTrace.action)}
        </div>
        <div class="evidence-card">
          <div class="evidence-title">Rubric / safety evidence</div>
          <div class="evidence-meta">${escapeHtml(item.evidence)}</div>
        </div>
        <div class="evidence-card">
          <div class="evidence-title">Boundary condition</div>
          <div class="evidence-meta">The prototype routes feedback for teacher review; it does not infer a final grade, replace teacher feedback, or use hidden gold labels at deployment time.</div>
        </div>
      </div>
    </div>
  `;
}

function renderSelect(name, label, options, labels) {
  return `
    <label>
      ${label}
      <select data-filter="${name}">
        ${options
          .map((value) => `<option value="${value}" ${state.queueFilters[name] === value ? "selected" : ""}>${labels[value] || value}</option>`)
          .join("")}
      </select>
    </label>
  `;
}

function renderTeacherQueue() {
  const filtered = feedbackItems.filter((item) => {
    const matchesRisk = state.queueFilters.risk === "all" || item.risk === state.queueFilters.risk;
    const matchesIssue = state.queueFilters.issue === "all" || item.issueType === state.queueFilters.issue;
    const matchesStatus = state.queueFilters.status === "all" || item.status === state.queueFilters.status;
    return matchesRisk && matchesIssue && matchesStatus;
  });

  viewRoot.innerHTML = `
    ${pageHeading(
      "Teacher queue",
      "Prioritize feedback that needs human judgment.",
      "The queue is designed for fast triage: meaning-change risks first, then medium-risk organization and development advice, while low-risk local edits stay visible but out of the main workload.",
      '<button class="button primary" data-page-jump="reports">Export report</button>'
    )}

    <div class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Queue filters</div>
          <div class="panel-subtitle">Filter by risk level, issue type, or current teacher status.</div>
        </div>
      </div>
      <div class="panel-body">
        <div class="filter-bar">
          ${renderSelect("risk", "Risk level", ["all", "high", "medium", "low"], { all: "All risks", ...riskLabels })}
          ${renderSelect("issue", "Issue type", ["all", "grammar", "vocabulary", "coherence", "organization", "task_response", "argument_clarity", "meaning_change", "overcorrection"], issueLabels)}
          ${renderSelect("status", "Status", ["all", "needs_teacher_review", "auto_accepted", "teacher_accepted", "teacher_edited", "teacher_rejected"], { all: "All statuses", ...statusLabels })}
          <label>
            Teacher
            <select disabled>
              <option>Current reviewer</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <div class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Feedback queue</div>
          <div class="panel-subtitle">${filtered.length} items shown from the synthetic demo set.</div>
        </div>
      </div>
      <div class="panel-body table-scroll">
        <table class="queue-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Essay</th>
              <th>Issue</th>
              <th>Risk</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${filtered
              .map((item) => {
                const session = sessions.find((essay) => essay.id === item.sessionId);
                return `
                  <tr class="${item.id === state.selectedFeedbackId ? "is-selected" : ""}">
                    <td>
                      <div class="row-title">${item.title}</div>
                      <div class="row-sub">${escapeHtml(item.aiSuggestion)}</div>
                    </td>
                    <td>${session ? session.id : item.sessionId}</td>
                    <td>${issueLabels[item.issueType]}</td>
                    <td>${riskBadge(item.risk)}</td>
                    <td>${statusChip(item.status)}</td>
                    <td><button class="button secondary" data-open-feedback="${item.id}">Review</button></td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderWritingRubric() {
  viewRoot.innerHTML = `
    ${pageHeading(
      "Writing rubric",
      "Make routing rules inspectable.",
      "The rubric page gives designers and teachers a concrete place to inspect review signals. It is not an external fact database or truth oracle; it is a transparent rule layer for safe ESL feedback release.",
      '<button class="button primary" data-page-jump="queue">Open teacher queue</button>'
    )}

    <div class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Routing rule table</div>
          <div class="panel-subtitle">Deploy-time signals used before teacher annotations are available.</div>
        </div>
      </div>
      <div class="panel-body table-scroll">
        <table class="queue-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Deploy-time signal</th>
              <th>Routing rule</th>
              <th>Example</th>
            </tr>
          </thead>
          <tbody>
            ${rubricRows
              .map(
                (row) => `
                <tr>
                  <td><div class="row-title">${row.dimension}</div></td>
                  <td>${escapeHtml(row.deploySignal)}</td>
                  <td>${escapeHtml(row.reviewRule)}</td>
                  <td>${escapeHtml(row.example)}</td>
                </tr>
              `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>

    <div class="grid three">
      ${metricCard("Low risk", "Auto accept", "Local language edits that preserve meaning")}
      ${metricCard("Medium risk", "Teacher review", "Organization, development, or coherence advice")}
      ${metricCard("High risk", "Teacher review", "Meaning change, overcorrection, or unsupported claims")}
    </div>
  `;
}

function renderReports() {
  const session = currentSession();
  const items = sessionItems(session.id);
  const review = items.filter((item) => item.group === "teacher_review");
  const auto = items.filter((item) => item.group === "auto_accept");
  const high = items.filter((item) => item.risk === "high");
  const reportText = `ConsensusScope ESL Writing Feedback Review Report

Essay ID: ${session.id}
Genre: ${session.essayGenre}
Draft: ${session.draftStage}

Routing summary
- ${auto.length} feedback items were auto accepted as low-risk local edits.
- ${review.length} feedback items were routed to teacher review.
- ${high.length} high-risk item(s) were flagged for meaning-change, overcorrection, or unsupported-claim risk.

Teacher-review items
${review.map((item) => `- ${item.id}: ${item.title} [${riskLabels[item.risk]}]`).join("\n")}

Limitations
- The report uses synthetic demo data.
- The system routes feedback for review; it does not grade essays or replace teacher judgment.
- Offline teacher annotations, if collected, must be reported separately from deploy-time routing signals.`;

  viewRoot.innerHTML = `
    ${pageHeading(
      "Reports",
      "Export a teacher-readable audit trail.",
      "Reports summarize auto-accepted local edits, review-routed items, routing reasons, teacher actions, and known limitations for reproducibility.",
      '<button class="button primary" id="copyReport">Copy report text</button>'
    )}

    <div class="grid four">
      ${metricCard("Session", session.id, session.essayGenre)}
      ${metricCard("Auto accepted", String(auto.length), "Low-risk local edits")}
      ${metricCard("Teacher review", String(review.length), "Needs human judgment")}
      ${metricCard("High risk", String(high.length), "Meaning or unsupported-content warning")}
    </div>

    <div class="report-preview" id="reportPreview">${escapeHtml(reportText)}</div>
  `;
}

function renderSettings() {
  viewRoot.innerHTML = `
    ${pageHeading(
      "Settings / diagnostics",
      "Keep technical configuration behind the teacher workflow.",
      "This page is for deployment and debugging controls. It stays secondary so the demo remains focused on Feedback Safety Graph review routing rather than raw model infrastructure.",
      ""
    )}

    <div class="settings-list">
      <div class="setting-row">
        <div>
          <div class="row-title">API mode</div>
          <div class="row-sub">Built-in demo key or user-provided key for public deployments.</div>
        </div>
        ${pill("Configured outside prototype", "pill--blue")}
      </div>
      <div class="setting-row">
        <div>
          <div class="row-title">Data privacy</div>
          <div class="row-sub">Student drafts should be anonymized before upload; this prototype stores only synthetic data.</div>
        </div>
        ${pill("PII removed")}
      </div>
      <div class="setting-row">
        <div>
          <div class="row-title">Diagnostics</div>
          <div class="row-sub">Raw model traces, parse errors, and API failures are visible to maintainers, not students.</div>
        </div>
        ${pill("Developer-facing")}
      </div>
      <div class="setting-row disabled-card">
        <div>
          <div class="row-title">Auxiliary QA reliability pages</div>
          <div class="row-sub">Earlier multi-model QA audit modules are kept outside the main ESL writing workflow.</div>
        </div>
        ${pill("Legacy")}
      </div>
    </div>
  `;
}

function render() {
  renderNav();
  if (state.page === "workspace") renderWorkspace();
  if (state.page === "review") renderEssayReview();
  if (state.page === "detail") renderFeedbackDetail();
  if (state.page === "queue") renderTeacherQueue();
  if (state.page === "rubric") renderWritingRubric();
  if (state.page === "reports") renderReports();
  if (state.page === "settings") renderSettings();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

document.addEventListener("click", (event) => {
  const navButton = event.target.closest("[data-page]");
  if (navButton) {
    state.page = navButton.dataset.page;
    render();
    return;
  }

  const jump = event.target.closest("[data-page-jump]");
  if (jump) {
    state.page = jump.dataset.pageJump;
    render();
    return;
  }

  const openSession = event.target.closest("[data-open-session]");
  if (openSession) {
    state.selectedSessionId = openSession.dataset.openSession;
    state.page = "review";
    render();
    return;
  }

  const openFeedback = event.target.closest("[data-open-feedback], [data-queue-feedback]");
  if (openFeedback) {
    const id = openFeedback.dataset.openFeedback || openFeedback.dataset.queueFeedback;
    const item = feedbackItems.find((feedback) => feedback.id === id);
    if (item) {
      state.selectedFeedbackId = id;
      state.selectedSessionId = item.sessionId;
      state.page = "detail";
      render();
    }
    return;
  }

  const decision = event.target.closest("[data-decision]");
  if (decision) {
    state.savedDecision = {
      feedbackId: state.selectedFeedbackId,
      status: decision.dataset.decision,
    };
    showToast(`Draft decision selected: ${statusLabels[decision.dataset.decision]}`);
    return;
  }

  if (event.target.closest("[data-edit-toggle]")) {
    const editBox = document.getElementById("editBox");
    if (editBox) editBox.classList.toggle("is-visible");
    return;
  }

  if (event.target.id === "saveDecisionButton") {
    const item = selectedFeedback();
    state.savedDecision = state.savedDecision || {
      feedbackId: item.id,
      status: "teacher_edited",
    };
    const success = document.getElementById("successMessage");
    if (success) success.classList.add("is-visible");
    showToast("Teacher decision saved locally in the prototype.");
    renderNav();
    return;
  }

  if (event.target.id === "copyReport") {
    const report = document.getElementById("reportPreview");
    if (report && navigator.clipboard) {
      navigator.clipboard.writeText(report.innerText);
    }
    showToast("Report text copied.");
  }
});

document.addEventListener("change", (event) => {
  const filter = event.target.closest("[data-filter]");
  if (!filter) return;
  state.queueFilters[filter.dataset.filter] = filter.value;
  renderTeacherQueue();
});

render();
