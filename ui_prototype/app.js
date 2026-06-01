const pages = [
  { id: "workspace", label: "Review Workspace" },
  { id: "essay", label: "Essay Review" },
  { id: "detail", label: "Feedback Detail" },
  { id: "queue", label: "Teacher Queue" },
  { id: "knowledge", label: "Knowledge Base" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings / Diagnostics" },
];

const riskLabels = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

const statusLabels = {
  auto_accepted: "Auto-accepted",
  needs_teacher_review: "Needs teacher review",
  teacher_accepted: "Teacher accepted",
  teacher_edited: "Teacher edited",
  teacher_rejected: "Teacher rejected",
  exported: "Exported",
};

const issueLabels = {
  grammar: "Grammar",
  style: "Style",
  literary_fact: "Literary fact",
  character_relation: "Character relation",
  theme_interpretation: "Theme interpretation",
  thesis_argument: "Thesis argument",
  citation: "Citation",
};

const evidenceLabels = {
  supported: "Supported",
  conflict: "Conflict",
  missing: "Missing",
  not_applicable: "Not applicable",
};

const sessions = [
  {
    id: "ESL-CL-007",
    title: "Essay 07: Frankenstein and Jane Eyre",
    assignment: "Comparative literature essay",
    works: "Frankenstein and Jane Eyre",
    level: "Upper-intermediate ESL",
    reviewMode: "Saved multi-LLM review",
    privacy: "Anonymized sample",
    status: "Ready for teacher review",
    reviewCount: 5,
    highRiskCount: 2,
    excerpt:
      "In both Frankenstein and Jane Eyre, the main characters struggle against social expectations and isolation. Frankenstein was published in 1918 and shows how Victor Frankenstein becomes the monster himself. Jane Eyre also explores independence, but the novel is mainly about colonialism rather than personal morality.",
  },
  {
    id: "ESL-CL-012",
    title: "Essay 12: The Great Gatsby and The Age of Innocence",
    assignment: "Comparative literature essay",
    works: "The Great Gatsby and The Age of Innocence",
    level: "Upper-intermediate ESL",
    reviewMode: "Saved multi-LLM review",
    privacy: "Anonymized sample",
    status: "Partially reviewed",
    reviewCount: 4,
    highRiskCount: 1,
    excerpt:
      "Both novels describe characters who want to escape social judgment, but Gatsby and Newland Archer are controlled by the same dream of freedom.",
  },
  {
    id: "ESL-CL-021",
    title: "Essay 21: The Scarlet Letter and The Awakening",
    assignment: "Comparative literature essay",
    works: "The Scarlet Letter and The Awakening",
    level: "Upper-intermediate ESL",
    reviewMode: "Saved multi-LLM review",
    privacy: "Anonymized sample",
    status: "Low-risk edits accepted",
    reviewCount: 2,
    highRiskCount: 0,
    excerpt:
      "The two texts both discuss social pressure on women, although the writers use different symbols and settings to show moral conflict.",
  },
];

const feedbackItems = [
  {
    id: "fb-001",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Frankenstein publication year conflict",
    issueType: "literary_fact",
    risk: "high",
    evidenceStatus: "supported",
    status: "needs_teacher_review",
    priority: "High",
    originalSpan: "Frankenstein was published in 1918...",
    feedback:
      "The publication year should be corrected, and the essay should explain that Mary Shelley's Frankenstein was first published in 1818.",
    suggestion:
      "Frankenstein was first published in 1818. Please verify the publication context and connect the correction to your comparison.",
    reason:
      "Knowledge base supports 1818, but the AI feedback must be reviewed because it changes a literary fact.",
    recommendation: "Teacher review",
    evidence: "Frankenstein → publication_year → 1818",
    group: "teacher_review",
    consensus: {
      models: 4,
      agreement: "3 / 4 models flagged a literary fact issue",
      minority: "1 model treated it as a simple grammar correction",
      parseErrors: 0,
    },
  },
  {
    id: "fb-002",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Victor Frankenstein / creature relation",
    issueType: "character_relation",
    risk: "high",
    evidenceStatus: "supported",
    status: "needs_teacher_review",
    priority: "High",
    originalSpan: "Victor Frankenstein becomes the monster himself.",
    feedback:
      "Clarify that Victor is the creator and that the creature is not literally Victor himself.",
    suggestion:
      "Victor Frankenstein creates the creature; he does not literally become the creature.",
    reason:
      "The feedback affects character interpretation and should be checked by a teacher.",
    recommendation: "Teacher review",
    evidence: "Victor is creator; the Creature is created being",
    group: "teacher_review",
    consensus: {
      models: 4,
      agreement: "4 / 4 models flagged a character relation issue",
      minority: "No minority warning",
      parseErrors: 0,
    },
  },
  {
    id: "fb-003",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Colonialism interpretation in Jane Eyre",
    issueType: "theme_interpretation",
    risk: "medium",
    evidenceStatus: "missing",
    status: "needs_teacher_review",
    priority: "Medium",
    originalSpan: "the novel is mainly about colonialism rather than personal morality",
    feedback:
      "The claim about colonialism may need textual evidence and should not replace the student's argument automatically.",
    suggestion:
      "If you discuss colonialism in Jane Eyre, connect it to specific passages and explain how it relates to personal morality.",
    reason:
      "Interpretation may be valid only with textual support; evidence is incomplete.",
    recommendation: "Teacher review",
    evidence: "Theme evidence incomplete",
    group: "teacher_review",
    consensus: {
      models: 4,
      agreement: "2 / 4 models flagged missing evidence",
      minority: "2 models treated it as a thesis issue",
      parseErrors: 0,
    },
  },
  {
    id: "fb-004",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Comparison criterion unclear",
    issueType: "thesis_argument",
    risk: "medium",
    evidenceStatus: "not_applicable",
    status: "needs_teacher_review",
    priority: "Medium",
    originalSpan: "both characters struggle against social expectations and isolation",
    feedback:
      "The comparison criterion should be clarified before the essay moves into separate claims about each novel.",
    suggestion:
      "State whether the comparison focuses on isolation, moral responsibility, or social expectations.",
    reason:
      "The suggestion changes argumentative framing and should remain teacher-facing.",
    recommendation: "Teacher review",
    evidence: "No direct KG conflict",
    group: "teacher_review",
    consensus: {
      models: 4,
      agreement: "3 / 4 models flagged a thesis issue",
      minority: "1 model suggested accepting directly",
      parseErrors: 0,
    },
  },
  {
    id: "fb-005",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Citation evidence needed for publication claim",
    issueType: "citation",
    risk: "medium",
    evidenceStatus: "supported",
    status: "needs_teacher_review",
    priority: "Medium",
    originalSpan: "Frankenstein was published in 1918",
    feedback:
      "Add citation or source context when correcting the publication year of Frankenstein.",
    suggestion:
      "Add a brief source-supported note that Frankenstein was first published in 1818.",
    reason:
      "The correction is knowledge-supported, but release should preserve classroom citation expectations.",
    recommendation: "Teacher review",
    evidence: "Frankenstein → publication_year → 1818",
    group: "teacher_review",
    consensus: {
      models: 4,
      agreement: "3 / 4 models requested citation context",
      minority: "1 model omitted citation support",
      parseErrors: 0,
    },
  },
  {
    id: "fb-006",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Grammar phrase improvement",
    issueType: "grammar",
    risk: "low",
    evidenceStatus: "not_applicable",
    status: "auto_accepted",
    priority: "Low",
    originalSpan: "the main characters struggle against social expectations",
    feedback:
      "Improve the phrase to 'the protagonists struggle against social expectations and isolation.'",
    suggestion:
      "Use 'the protagonists' to avoid repeating 'main characters' in a formal essay.",
    reason: "Local grammar/style edit, no literary meaning change.",
    recommendation: "Auto-accept",
    evidence: "No KG check required",
    group: "auto",
    consensus: {
      models: 4,
      agreement: "4 / 4 models treated it as local style",
      minority: "No minority warning",
      parseErrors: 0,
    },
  },
  {
    id: "fb-007",
    sessionId: "ESL-CL-007",
    essay: "Essay 07",
    title: "Fluency improvement for 'also explores'",
    issueType: "style",
    risk: "low",
    evidenceStatus: "not_applicable",
    status: "auto_accepted",
    priority: "Low",
    originalSpan: "Jane Eyre also explores independence",
    feedback:
      "Use a more fluent transition: 'Jane Eyre similarly explores independence.'",
    suggestion:
      "Jane Eyre similarly explores independence, but through a different moral and social framework.",
    reason: "Fluency edit with no factual claim.",
    recommendation: "Auto-accept",
    evidence: "No KG check required",
    group: "auto",
    consensus: {
      models: 4,
      agreement: "4 / 4 models treated it as local style",
      minority: "No minority warning",
      parseErrors: 0,
    },
  },
  {
    id: "fb-012",
    sessionId: "ESL-CL-012",
    essay: "Essay 12",
    title: "Jane Eyre character relation",
    issueType: "character_relation",
    risk: "high",
    evidenceStatus: "conflict",
    status: "needs_teacher_review",
    priority: "High",
    originalSpan: "Jane and Rochester have the same social position.",
    feedback:
      "Check whether the feedback changes the relation between Jane and Rochester.",
    suggestion:
      "Clarify that Jane and Rochester occupy different social positions for much of the novel.",
    reason: "Feedback changes the relation between Jane and Rochester.",
    recommendation: "Teacher review",
    evidence: "Jane Eyre → central_character → Jane Eyre; Rochester relation requires context",
    group: "teacher_review",
    consensus: { models: 4, agreement: "3 / 4 models flagged relation risk", minority: "1 model accepted", parseErrors: 0 },
  },
  {
    id: "fb-021",
    sessionId: "ESL-CL-021",
    essay: "Essay 21",
    title: "Local grammar edit",
    issueType: "grammar",
    risk: "low",
    evidenceStatus: "not_applicable",
    status: "auto_accepted",
    priority: "Low",
    originalSpan: "the writers uses",
    feedback: "Change 'uses' to 'use' for subject-verb agreement.",
    suggestion: "The writers use different symbols and settings.",
    reason: "Subject-verb agreement edit with no meaning change.",
    recommendation: "Auto-accept",
    evidence: "No KG check required",
    group: "auto",
    consensus: { models: 4, agreement: "4 / 4 models agreed", minority: "No minority warning", parseErrors: 0 },
  },
];

const knowledgeEvidence = [
  { entity: "Frankenstein", relation: "author", value: "Mary Shelley", source: "curated KG", used: "yes", status: "supported" },
  { entity: "Frankenstein", relation: "publication_year", value: "1818", source: "curated KG", used: "yes", status: "supported" },
  { entity: "Frankenstein", relation: "genre", value: "Gothic novel", source: "curated KG", used: "yes", status: "supported" },
  { entity: "Victor Frankenstein", relation: "role", value: "creator", source: "curated KG", used: "yes", status: "supported" },
  { entity: "The Creature", relation: "role", value: "created being", source: "curated KG", used: "yes", status: "supported" },
];

const state = {
  page: "workspace",
  selectedSessionId: "ESL-CL-007",
  selectedFeedbackId: "fb-001",
  selectedQueueId: "fb-001",
  editingFeedback: false,
  savedDecision: false,
  filters: {
    risk: "all",
    issue: "all",
    evidence: "all",
    status: "all",
  },
};

const navRoot = document.getElementById("sideNav");
const viewRoot = document.getElementById("viewRoot");
const toastRoot = document.getElementById("toast");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function riskBadge(risk) {
  return `<span class="risk-badge risk-${risk}">${riskLabels[risk] || risk}</span>`;
}

function statusChip(status) {
  const cls = {
    auto_accepted: "status-auto",
    needs_teacher_review: "status-review",
    teacher_edited: "status-edited",
    teacher_accepted: "status-auto",
    teacher_rejected: "status-rejected",
    exported: "status-exported",
  }[status] || "pill--neutral";
  return `<span class="status-chip ${cls}">${statusLabels[status] || status}</span>`;
}

function evidenceChip(status) {
  const cls = {
    supported: "status-auto",
    conflict: "status-review",
    missing: "pill--blue",
    not_applicable: "pill--neutral",
  }[status] || "pill--neutral";
  return `<span class="status-chip ${cls}">${evidenceLabels[status] || status}</span>`;
}

function showToast(message) {
  toastRoot.textContent = message;
  toastRoot.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toastRoot.classList.remove("is-visible");
  }, 2200);
}

function getSelectedSession() {
  return sessions.find((session) => session.id === state.selectedSessionId) || sessions[0];
}

function getSelectedFeedback() {
  return feedbackItems.find((item) => item.id === state.selectedFeedbackId) || feedbackItems[0];
}

function getSessionFeedback(sessionId = state.selectedSessionId) {
  return feedbackItems.filter((item) => item.sessionId === sessionId);
}

function setPage(pageId) {
  state.page = pageId;
  state.editingFeedback = false;
  render();
}

function setSession(sessionId) {
  state.selectedSessionId = sessionId;
  const first = getSessionFeedback(sessionId)[0];
  if (first) {
    state.selectedFeedbackId = first.id;
    state.selectedQueueId = first.id;
  }
}

function inspectFeedback(itemId) {
  state.selectedFeedbackId = itemId;
  state.selectedQueueId = itemId;
  state.page = "detail";
  state.editingFeedback = false;
  state.savedDecision = false;
  render();
}

function renderNav() {
  navRoot.innerHTML = pages
    .map(
      (page) => `
        <button class="nav-button ${state.page === page.id ? "is-active" : ""}" data-page="${page.id}">
          ${page.label}
        </button>
      `,
    )
    .join("");

  navRoot.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.page));
  });
}

function pageShell(eyebrow, title, copy, actions = "") {
  return `
    <section class="page-heading">
      <div>
        <div class="eyebrow">${eyebrow}</div>
        <h1>${title}</h1>
        <p class="page-copy">${copy}</p>
      </div>
      <div class="actions">${actions}</div>
    </section>
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

function queuePreviewRow(item, actionText = "Review now") {
  return `
    <tr>
      <td>${riskBadge(item.risk)}</td>
      <td><div class="row-title">${escapeHtml(item.title)}</div><div class="row-sub">Essay: ${escapeHtml(item.essay)}</div></td>
      <td>${issueLabels[item.issueType]}</td>
      <td class="row-sub">${escapeHtml(item.reason)}</td>
      <td><button class="button" data-inspect="${item.id}">${actionText}</button></td>
    </tr>
  `;
}

function renderWorkspace() {
  const priority = [
    feedbackItems.find((item) => item.id === "fb-001"),
    feedbackItems.find((item) => item.id === "fb-012"),
    feedbackItems.find((item) => item.id === "fb-003"),
    feedbackItems.find((item) => item.id === "fb-021"),
  ].filter(Boolean);

  viewRoot.innerHTML = `
    ${pageShell(
      "Review Workspace",
      "Prioritize AI feedback that may change literary facts, interpretation, or student meaning.",
      "Low-risk grammar and style edits can be accepted automatically. Feedback that changes literary facts, character relations, themes, thesis, or interpretation is routed to teacher review.",
      '<button class="button primary" data-go-essay="ESL-CL-007">Open current review</button>',
    )}

    <section class="grid five">
      ${metricCard("Total feedback items", "59", "Generated across the ESL demo set")}
      ${metricCard("Auto-accepted local edits", "14", "Low-risk grammar/style edits")}
      ${metricCard("Teacher-review items", "45", "Routed to human review")}
      ${metricCard("High-risk items", "20", "Literary fact or meaning risk")}
      ${metricCard("KG-supported decisions", "23", "Linked to knowledge evidence")}
    </section>

    <section class="routing-card">
      <strong>Routing explanation.</strong>
      Low-risk grammar and style edits can be accepted automatically. Feedback that changes literary facts, character relations, themes, thesis, or interpretation is routed to teacher review.
    </section>

    <section class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Priority Queue Preview</div>
          <div class="panel-subtitle">Items shown here are mock data for designer-facing workflow review.</div>
        </div>
      </div>
      <div class="panel-body table-scroll">
        <table class="queue-table">
          <thead>
            <tr><th>Risk</th><th>Case</th><th>Issue type</th><th>Reason</th><th>Action</th></tr>
          </thead>
          <tbody>
            ${queuePreviewRow(priority[0], "Review now")}
            ${queuePreviewRow(priority[1], "Review now")}
            ${queuePreviewRow(priority[2], "Inspect evidence")}
            ${queuePreviewRow(priority[3], "Auto-accepted")}
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">Recent Essay Sessions</div>
          <div class="panel-subtitle">Open Review switches to the Essay Review page using mock JavaScript state.</div>
        </div>
      </div>
      <div class="panel-body grid three">
        ${sessions
          .map(
            (session) => `
              <article class="session-card">
                <div class="session-card__title">${escapeHtml(session.title)}</div>
                <div class="session-meta">
                  Status: ${escapeHtml(session.status)}<br>
                  Review count: ${session.reviewCount}<br>
                  High-risk count: ${session.highRiskCount}
                </div>
                <button class="button" data-go-essay="${session.id}">Open Review</button>
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderEssayReview() {
  const session = getSelectedSession();
  const items = getSessionFeedback(session.id);
  const auto = items.filter((item) => item.group === "auto");
  const review = items.filter((item) => item.group === "teacher_review");

  viewRoot.innerHTML = `
    ${pageShell(
      "Essay Review",
      "Review one ESL comparative-literature essay.",
      "This page shows the main review flow: context, anonymized excerpt, routing summary, and feedback items grouped by teacher action.",
      '<button class="button secondary" data-page-shortcut="workspace">Back to workspace</button><button class="button primary" data-page-shortcut="reports">Create report</button>',
    )}

    <section class="panel shadow">
      <div class="panel-header">
        <div>
          <div class="panel-title">Essay Context</div>
          <div class="panel-subtitle">Saved multi-LLM review with anonymized sample data.</div>
        </div>
        <span class="pill pill--blue">Saved multi-LLM review</span>
      </div>
      <div class="panel-body">
        <div class="essay-context">
          <div class="context-item"><div class="context-label">Essay ID</div><div class="context-value">${session.id}</div></div>
          <div class="context-item"><div class="context-label">Assignment</div><div class="context-value">${session.assignment}</div></div>
          <div class="context-item"><div class="context-label">Works compared</div><div class="context-value">${session.works}</div></div>
          <div class="context-item"><div class="context-label">Student level</div><div class="context-value">${session.level}</div></div>
          <div class="context-item"><div class="context-label">Review mode</div><div class="context-value">${session.reviewMode}</div></div>
          <div class="context-item"><div class="context-label">Privacy</div><div class="context-value">${session.privacy}</div></div>
        </div>
      </div>
    </section>

    <section class="grid two">
      <article class="panel">
        <div class="panel-header"><div><div class="panel-title">Essay Excerpt</div><div class="panel-subtitle">Synthetic text with intentional literary issues for demonstration.</div></div></div>
        <div class="panel-body"><div class="essay-excerpt">${escapeHtml(session.excerpt)}</div></div>
      </article>

      <aside class="panel">
        <div class="panel-header"><div><div class="panel-title">Routing Summary</div><div class="panel-subtitle">The teacher sees action distribution, not raw model calls.</div></div></div>
        <div class="panel-body grid">
          ${metricCard("Feedback items generated", String(items.length), "Unified FeedbackItem objects")}
          ${metricCard("Auto-accepted", String(auto.length), "Local grammar/style edits")}
          ${metricCard("Require teacher review", String(review.length), "Factual, interpretive, or thesis risk")}
          ${metricCard("KG checks triggered", "3", "Knowledge evidence inspected")}
        </div>
      </aside>
    </section>

    <section class="panel shadow">
      <div class="panel-header"><div><div class="panel-title">Feedback List</div><div class="panel-subtitle">Each item has Inspect, Accept, Edit, and Reject actions.</div></div></div>
      <div class="panel-body">
        <div class="feedback-group-title">Group 1: Auto-accepted local edits</div>
        <div class="grid">
          ${auto.map(renderFeedbackItemCard).join("")}
        </div>

        <div class="feedback-group-title">Group 2: Teacher-review required</div>
        <div class="grid">
          ${review.map(renderFeedbackItemCard).join("")}
        </div>
      </div>
    </section>
  `;
}

function renderFeedbackItemCard(item) {
  return `
    <article class="feedback-item-card ${item.risk}">
      <div class="feedback-card-head">
        <div>
          <div class="feedback-card-title">${issueLabels[item.issueType]}: ${escapeHtml(item.title)}</div>
          <div class="feedback-card-copy">${escapeHtml(item.reason)}</div>
        </div>
        ${riskBadge(item.risk)}
      </div>
      <div class="chip-row">
        ${statusChip(item.status)}
        ${evidenceChip(item.evidenceStatus)}
        <span class="pill pill--neutral">Recommended action: ${escapeHtml(item.recommendation)}</span>
      </div>
      <div class="teacher-action-toolbar">
        <button class="button primary" data-inspect="${item.id}">Inspect</button>
        <button class="button" data-simple-action="Accepted ${escapeHtml(item.title)}">Accept</button>
        <button class="button" data-simple-action="Opened edit state for ${escapeHtml(item.title)}">Edit</button>
        <button class="button danger" data-simple-action="Rejected ${escapeHtml(item.title)}">Reject</button>
      </div>
    </article>
  `;
}

function renderFeedbackDetail() {
  const item = getSelectedFeedback();
  const displayStatus = state.savedDecision && item.id === "fb-001" ? "teacher_edited" : item.status;
  viewRoot.innerHTML = `
    ${pageShell(
      "Feedback Detail",
      escapeHtml(item.title),
      "This page explains why a specific feedback item can be released, edited, rejected, or routed for teacher review.",
      '<button class="button secondary" data-page-shortcut="essay">Back to essay</button><button class="button primary" data-page-shortcut="queue">Open queue</button>',
    )}

    <section class="detail-layout">
      <article class="panel shadow">
        <div class="panel-header">
          <div>
            <div class="panel-title">Feedback Decision</div>
            <div class="panel-subtitle">Teacher-readable explanation first; raw traces stay hidden.</div>
          </div>
          ${statusChip(displayStatus)}
        </div>
        <div class="panel-body grid">
          <div class="essay-excerpt"><strong>Original student span</strong><br>${escapeHtml(item.originalSpan)}</div>
          <div class="feedback-item-card ${item.risk}">
            <div class="feedback-card-title">AI-generated feedback</div>
            <div class="feedback-card-copy">${escapeHtml(item.feedback)}</div>
          </div>
          <div class="risk-decision-card">
            <div class="chip-row">
              ${riskBadge(item.risk)}
              <span class="pill pill--neutral">Issue type: ${issueLabels[item.issueType]}</span>
              <span class="pill pill--neutral">Status: ${statusLabels[displayStatus]}</span>
            </div>
            <div style="height:10px"></div>
            <strong>Recommended action:</strong> ${escapeHtml(item.recommendation)}
          </div>
          <div class="explain-box">
            <strong>Why teacher review is recommended.</strong>
            This feedback changes a literary fact or interpretation. The knowledge base supports the relevant evidence, but because the correction affects literary knowledge rather than only grammar, ConsensusScope routes it to teacher review.
          </div>

          <div class="teacher-action-toolbar">
            <button class="button" data-simple-action="Feedback accepted">Accept feedback</button>
            <button class="button primary" id="editFeedbackButton">Edit feedback</button>
            <button class="button danger" data-simple-action="Feedback rejected">Reject feedback</button>
            <button class="button" data-simple-action="Teacher note added">Add note</button>
          </div>

          <div class="edit-box ${state.editingFeedback ? "is-visible" : ""}" id="editBox">
            <label>
              Edited feedback
              <textarea id="editedFeedbackText">${escapeHtml(item.suggestion)}</textarea>
            </label>
            <div style="height:10px"></div>
            <button class="button primary" id="saveDecisionButton">Save teacher decision</button>
          </div>

          <div class="success-message ${state.savedDecision ? "is-visible" : ""}" id="saveMessage">
            Teacher decision saved. Status: Teacher edited.
          </div>
        </div>
      </article>

      <aside class="grid">
        <section class="panel shadow">
          <div class="panel-header"><div><div class="panel-title">Knowledge Evidence</div><div class="panel-subtitle">EvidenceCard components.</div></div></div>
          <div class="panel-body grid">
            ${knowledgeEvidence.slice(0, 3).map(renderEvidenceCard).join("")}
          </div>
        </section>

        <section class="panel shadow">
          <div class="panel-header"><div><div class="panel-title">Multi-LLM Consensus Summary</div><div class="panel-subtitle">Teacher-facing summary, not raw JSON.</div></div></div>
          <div class="panel-body">
            <div class="setting-row"><span>Models reviewed</span><strong>${item.consensus.models}</strong></div>
            <div class="setting-row"><span>Agreement</span><strong>${escapeHtml(item.consensus.agreement)}</strong></div>
            <div class="setting-row"><span>Minority warning</span><strong>${escapeHtml(item.consensus.minority)}</strong></div>
            <div class="setting-row"><span>Parse errors</span><strong>${item.consensus.parseErrors}</strong></div>
          </div>
        </section>
      </aside>
    </section>
  `;
}

function renderEvidenceCard(item) {
  return `
    <article class="evidence-card">
      <div class="evidence-title">Work: ${escapeHtml(item.entity)}</div>
      <div class="evidence-meta">
        Relation: ${escapeHtml(item.relation)}<br>
        Value: ${escapeHtml(item.value)}
      </div>
      ${evidenceChip(item.status)}
    </article>
  `;
}

function renderTeacherQueue() {
  const visible = feedbackItems.filter((item) => {
    const f = state.filters;
    return (
      (f.risk === "all" || item.risk === f.risk) &&
      (f.issue === "all" || item.issueType === f.issue) &&
      (f.evidence === "all" || item.evidenceStatus === f.evidence) &&
      (f.status === "all" || item.status === f.status)
    );
  });
  const selected = feedbackItems.find((item) => item.id === state.selectedQueueId) || visible[0] || feedbackItems[0];

  viewRoot.innerHTML = `
    ${pageShell(
      "Teacher Queue",
      "Review all feedback that needs teacher judgment.",
      "The queue supports filtering by risk, issue type, evidence status, and review status. Rows are selectable and can open the Feedback Detail page.",
      '<button class="button secondary is-disabled" disabled>Mark selected as reviewed</button><button class="button">Export queue</button>',
    )}

    <section class="panel">
      <div class="panel-header"><div><div class="panel-title">Filter Bar</div><div class="panel-subtitle">Simple mock filtering is implemented in JavaScript.</div></div></div>
      <div class="panel-body filter-bar">
        ${renderSelect("risk", "Risk", ["all", "low", "medium", "high"], riskLabels)}
        ${renderSelect("issue", "Issue type", ["all", "grammar", "style", "literary_fact", "character_relation", "theme_interpretation", "thesis_argument", "citation"], issueLabels)}
        ${renderSelect("evidence", "Evidence", ["all", "supported", "conflict", "missing", "not_applicable"], evidenceLabels)}
        ${renderSelect("status", "Status", ["all", "needs_teacher_review", "auto_accepted", "teacher_accepted", "teacher_edited", "teacher_rejected"], statusLabels)}
      </div>
    </section>

    <section class="grid two">
      <article class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Queue Table</div><div class="panel-subtitle">${visible.length} mock rows match current filters.</div></div></div>
        <div class="panel-body table-scroll">
          <table class="queue-table">
            <thead><tr><th>Priority</th><th>Essay</th><th>Issue type</th><th>Risk</th><th>Evidence</th><th>Recommendation</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              ${visible.map(renderQueueRow).join("") || '<tr><td colspan="8">No items match the current filters.</td></tr>'}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="detail-drawer">
        <div class="panel-title">Selected Item</div>
        <div class="row-title">${escapeHtml(selected.title)}</div>
        <div class="row-sub">${escapeHtml(selected.reason)}</div>
        <div class="chip-row">${riskBadge(selected.risk)}${evidenceChip(selected.evidenceStatus)}${statusChip(selected.status)}</div>
        <button class="button primary" data-inspect="${selected.id}">Open detail</button>
      </aside>
    </section>
  `;
}

function renderSelect(key, label, values, labels) {
  return `
    <label>
      ${label}
      <select data-filter="${key}">
        ${values
          .map((value) => `<option value="${value}" ${state.filters[key] === value ? "selected" : ""}>${value === "all" ? "All" : labels[value] || value}</option>`)
          .join("")}
      </select>
    </label>
  `;
}

function renderQueueRow(item) {
  return `
    <tr data-row="${item.id}" class="${state.selectedQueueId === item.id ? "is-selected" : ""}">
      <td>${escapeHtml(item.priority)}</td>
      <td><div class="row-title">${escapeHtml(item.essay)}</div><div class="row-sub">${escapeHtml(item.title)}</div></td>
      <td>${issueLabels[item.issueType]}</td>
      <td>${riskBadge(item.risk)}</td>
      <td>${evidenceChip(item.evidenceStatus)}</td>
      <td>${escapeHtml(item.recommendation)}</td>
      <td>${statusChip(item.status)}</td>
      <td><button class="button" data-inspect="${item.id}">Open detail</button></td>
    </tr>
  `;
}

function renderKnowledgeBase() {
  viewRoot.innerHTML = `
    ${pageShell(
      "Knowledge Base",
      "Inspect the literary evidence behind review routing.",
      "This page demonstrates knowledge-grounded behavior using curated mock evidence for works, authors, characters, themes, and relations.",
      '<button class="button">Import course readings</button><button class="button primary">Add evidence</button>',
    )}

    <section class="panel shadow">
      <div class="panel-header"><div><div class="panel-title">Search</div><div class="panel-subtitle">Search works, authors, characters, themes...</div></div></div>
      <div class="panel-body">
        <input value="Frankenstein" aria-label="Search works, authors, characters, themes">
      </div>
    </section>

    <section class="grid five">
      ${metricCard("Works", "30", "Commonly taught works")}
      ${metricCard("KG triples", "319", "Curated evidence rows")}
      ${metricCard("Authors", "30", "Author profiles")}
      ${metricCard("Characters", "84", "Central characters")}
      ${metricCard("Themes", "90", "Theme labels")}
    </section>

    <section class="kg-profile">
      <article class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Entity Profile</div><div class="panel-subtitle">Default example: Frankenstein.</div></div></div>
        <div class="panel-body grid">
          <div class="context-item"><div class="context-label">Work</div><div class="context-value">Frankenstein</div></div>
          <div class="context-item"><div class="context-label">Author</div><div class="context-value">Mary Shelley</div></div>
          <div class="context-item"><div class="context-label">Publication year</div><div class="context-value">1818</div></div>
          <div class="context-item"><div class="context-label">Genre</div><div class="context-value">Gothic novel</div></div>
          <div class="context-item"><div class="context-label">Characters</div><div class="context-value">Victor Frankenstein, the Creature, Elizabeth Lavenza</div></div>
          <div class="theme-list">
            <span class="pill pill--blue">creation</span>
            <span class="pill pill--blue">isolation</span>
            <span class="pill pill--blue">responsibility</span>
            <span class="pill pill--blue">knowledge</span>
          </div>
        </div>
      </article>

      <aside class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Evidence Status Legend</div><div class="panel-subtitle">Badges use text and color.</div></div></div>
        <div class="panel-body grid">
          <div class="setting-row"><span>Supported</span>${evidenceChip("supported")}</div>
          <div class="setting-row"><span>Conflict</span>${evidenceChip("conflict")}</div>
          <div class="setting-row"><span>Missing</span>${evidenceChip("missing")}</div>
          <div class="setting-row"><span>Not applicable</span>${evidenceChip("not_applicable")}</div>
        </div>
      </aside>
    </section>

    <section class="panel shadow">
      <div class="panel-header"><div><div class="panel-title">Triple Table</div><div class="panel-subtitle">Evidence used in review decisions.</div></div></div>
      <div class="panel-body table-scroll">
        <table class="queue-table">
          <thead><tr><th>Entity</th><th>Relation</th><th>Value</th><th>Source</th><th>Used in review?</th></tr></thead>
          <tbody>
            ${knowledgeEvidence
              .map((row) => `<tr><td>${escapeHtml(row.entity)}</td><td>${escapeHtml(row.relation)}</td><td>${escapeHtml(row.value)}</td><td>${escapeHtml(row.source)}</td><td>${escapeHtml(row.used)}</td></tr>`)
              .join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderReports() {
  const report = `# ConsensusScope Review Report

Essay ID: ESL-CL-007
Assignment: Comparative literature essay
Works compared: Frankenstein and Jane Eyre

## Routing Summary
- 2 low-risk local edits were auto-accepted.
- 5 feedback items were routed to teacher review.
- 3 decisions used literary knowledge-base evidence.

## Teacher-reviewed item
Issue: Frankenstein publication year
Risk: High
Evidence: Frankenstein → publication_year → 1818
Teacher decision: Edited feedback before release to student.

## Limitation
ConsensusScope supports teacher review routing. It does not replace teacher judgment.`;

  viewRoot.innerHTML = `
    ${pageShell(
      "Reports",
      "Export a teacher-readable review report.",
      "This page demonstrates how the system can produce an audit trail for accepted edits, teacher-reviewed items, evidence, and limitations.",
      '<button class="button primary" data-export="Markdown">Export Markdown</button><button class="button" data-export="JSON">Export JSON</button><button class="button" data-export="CSV">Export CSV</button>',
    )}

    <section class="grid three">
      ${metricCard("Session", "ESL-CL-007", "Frankenstein and Jane Eyre")}
      ${metricCard("Total feedback items", "7", "Generated in saved review")}
      ${metricCard("Auto-accepted", "2", "Low-risk local edits")}
      ${metricCard("Teacher review", "5", "Human judgment required")}
      ${metricCard("Teacher edited", "1", "Decision saved in prototype")}
      ${metricCard("Teacher rejected", "1", "Mock report value")}
    </section>

    <section class="panel shadow">
      <div class="panel-header"><div><div class="panel-title">Report Preview</div><div class="panel-subtitle">Markdown-style preview for conference recording.</div></div></div>
      <div class="panel-body"><pre class="report-preview">${escapeHtml(report)}</pre></div>
    </section>
  `;
}

function renderSettings() {
  viewRoot.innerHTML = `
    ${pageShell(
      "Settings / Diagnostics",
      "Keep technical diagnostics secondary.",
      "This low-priority page prevents API configuration, raw traces, and auxiliary QA reliability from taking over the main teacher workflow.",
      '<button class="button secondary">Reset demo state</button>',
    )}

    <section class="grid three">
      <article class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Demo Mode</div><div class="panel-subtitle">No live calls in this prototype.</div></div></div>
        <div class="panel-body settings-list">
          <div class="setting-row"><span>Saved demo data</span><strong>On</strong></div>
          <div class="setting-row"><span>Live API calls</span><strong>Off</strong></div>
          <div class="setting-row"><span>Student PII storage</span><strong>Off</strong></div>
        </div>
      </article>

      <article class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Model Providers</div><div class="panel-subtitle">Saved outputs available.</div></div></div>
        <div class="panel-body settings-list">
          ${["DeepSeek", "Qwen", "GLM", "Kimi"].map((provider) => `<div class="setting-row"><span>${provider}</span><strong>Saved outputs available</strong></div>`).join("")}
        </div>
      </article>

      <article class="panel shadow">
        <div class="panel-header"><div><div class="panel-title">Auxiliary QA Reliability Module</div><div class="panel-subtitle">Clearly marked as auxiliary.</div></div></div>
        <div class="panel-body">
          <div class="explain-box">ConsensusScope also contains auxiliary multi-model QA audit pages used during earlier reliability testing. They are not the main ESL feedback workflow.</div>
        </div>
      </article>
    </section>

    <section class="panel" style="margin-top: 14px;">
      <div class="panel-header"><div><div class="panel-title">Developer Diagnostics</div><div class="panel-subtitle">Disabled placeholders for non-teacher users.</div></div></div>
      <div class="panel-body grid four">
        <div class="session-card disabled-card"><div class="session-card__title">Raw traces</div><div class="session-meta">Collapsed by default</div></div>
        <div class="session-card disabled-card"><div class="session-card__title">Parse status</div><div class="session-meta">Developer-only</div></div>
        <div class="session-card disabled-card"><div class="session-card__title">Routing logs</div><div class="session-meta">Developer-only</div></div>
        <div class="session-card disabled-card"><div class="session-card__title">Test data</div><div class="session-meta">Mock data only</div></div>
      </div>
    </section>
  `;
}

function attachEvents() {
  viewRoot.querySelectorAll("[data-go-essay]").forEach((button) => {
    button.addEventListener("click", () => {
      setSession(button.dataset.goEssay);
      state.page = "essay";
      render();
    });
  });

  viewRoot.querySelectorAll("[data-page-shortcut]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.pageShortcut));
  });

  viewRoot.querySelectorAll("[data-inspect]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      inspectFeedback(button.dataset.inspect);
    });
  });

  viewRoot.querySelectorAll("[data-simple-action]").forEach((button) => {
    button.addEventListener("click", () => showToast(button.dataset.simpleAction));
  });

  viewRoot.querySelectorAll("[data-export]").forEach((button) => {
    button.addEventListener("click", () => showToast(`Demo ${button.dataset.export} export generated.`));
  });

  viewRoot.querySelectorAll("[data-filter]").forEach((select) => {
    select.addEventListener("change", () => {
      state.filters[select.dataset.filter] = select.value;
      render();
    });
  });

  viewRoot.querySelectorAll("[data-row]").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedQueueId = row.dataset.row;
      render();
    });
  });

  const editButton = document.getElementById("editFeedbackButton");
  if (editButton) {
    editButton.addEventListener("click", () => {
      state.editingFeedback = true;
      state.savedDecision = false;
      render();
    });
  }

  const saveButton = document.getElementById("saveDecisionButton");
  if (saveButton) {
    saveButton.addEventListener("click", () => {
      state.savedDecision = true;
      state.editingFeedback = false;
      const item = getSelectedFeedback();
      item.status = "teacher_edited";
      showToast("Teacher decision saved.");
      render();
    });
  }
}

function render() {
  renderNav();
  const renderers = {
    workspace: renderWorkspace,
    essay: renderEssayReview,
    detail: renderFeedbackDetail,
    queue: renderTeacherQueue,
    knowledge: renderKnowledgeBase,
    reports: renderReports,
    settings: renderSettings,
  };
  renderers[state.page]();
  attachEvents();
}

render();
