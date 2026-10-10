const API_BASE = window.CDSS_API_URL || (window.location.origin.includes(':8000') ? '' : 'http://127.0.0.1:8000');

const resourceConfig = {
  conditions: { label: 'Conditions', singular: 'condition' },
  symptoms: { label: 'Symptoms', singular: 'symptom' },
  'risk-factors': { label: 'Risk Factors', singular: 'risk factor' },
  tests: { label: 'Tests', singular: 'test' },
  treatments: { label: 'Treatments', singular: 'treatment' },
};

const state = {
  page: 'home',
  stats: null,
  data: {},
  selectedSymptoms: [],
  selectedRisks: [],
  selectedNegativeSymptoms: [],
  completedTests: [],
  results: null,
  error: '',
  loading: false,
  addType: 'conditions',
  addLoading: false,
  addError: '',
  kbQuery: '',
  symptomsQuery: '',
  risksQuery: '',
  negativeSymptomsQuery: '',
  completedTestsQuery: '',
};

const app = document.querySelector('#app');

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    let message = 'The clinical decision support service could not complete that request.';
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch (_) {
      // ignore invalid JSON and keep the fallback message
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function titleBar() {
  return `
    <header class="app-header">
      <div class="brand-block">
        <a class="brand" href="#" data-page="home">
          <span class="brand-mark"></span>
          <span>Genassist CDSS</span>
        </a>
        <span class="title-tag">Clinical Decision Support</span>
      </div>

      <nav class="top-nav" aria-label="Main navigation">
        <a href="#" data-page="home">Home</a>
        <a href="#" data-page="overview">Workspace</a>
        <a href="#" data-page="knowledge">Knowledge Base</a>
        <a href="#" data-page="add">Add Records</a>
        <a href="#" data-page="evaluate">Evaluation</a>
      </nav>

      <div class="header-actions">
        <button class="pill pill-light" data-page="evaluate">Start Evaluation</button>
      </div>
    </header>
  `;
}

function render() {
  if (!app) return;

  const activeSearch = document.activeElement?.matches('input[data-search], #kb-search')
    ? {
      id: document.activeElement.id,
      type: document.activeElement.dataset.search,
      selectionStart: document.activeElement.selectionStart,
      selectionEnd: document.activeElement.selectionEnd,
    }
    : null;

  const content = state.page === 'home'
    ? landingPage()
    : state.page === 'overview'
      ? overviewPage()
      : state.page === 'evaluate'
        ? evaluationPage()
        : state.page === 'results'
          ? resultsPage()
          : state.page === 'add'
            ? addRecordsPage()
          : state.page === 'knowledge'
            ? knowledgePage('conditions')
            : state.page.startsWith('knowledge:')
              ? knowledgePage(state.page.split(':')[1] || 'conditions')
              : overviewPage();

  app.innerHTML = `${titleBar()}<main class="main-shell">${content}</main>`;
  bindEvents();

  if (activeSearch) {
    const selector = activeSearch.id ? `#${activeSearch.id}` : `input[data-search="${activeSearch.type}"]`;
    const input = app.querySelector(selector);
    input?.focus({ preventScroll: true });
    input?.setSelectionRange(activeSearch.selectionStart, activeSearch.selectionEnd);
  }
}

function landingPage() {
  return `
    <main class="landing">
      <section class="hero">
        <div>
          <span class="eyebrow">Clinical decision support</span>
          <h1>Make clinical decisions with greater clarity.</h1>
          <p class="hero-copy">
            Analyze patient symptoms and risk factors to identify candidate conditions, prioritize urgency,
            and review suggested tests and treatments from the local knowledge base.
          </p>
          <div class="hero-actions">
            <button class="pill" data-page="evaluate">Start Evaluation</button>
            <button class="pill light" data-page="knowledge">Explore Knowledge Base</button>
          </div>
          <div class="trust"><i></i> Connected to the local decision-support database</div>
        </div>
        <div class="mockup">
          <div class="mockup-top">
            <div><span class="kicker">Live assessment</span><h3>Clinical CDSS</h3></div>
            <span class="status">System Online</span>
          </div>
          <div class="mock-label">Common Stored Symptoms</div>
          <div class="tags">
            <span class="tag">Fever</span>
            <span class="tag">Cough</span>
            <span class="tag">Shortness of breath</span>
          </div>
          <div class="mock-label">Possible Conditions</div>
          <div class="mock-results">
            <div class="result-row">
              <div>Pneumonia<div class="bar"><b style="width:85%"></b></div></div>
              <span class="score">85%</span>
            </div>
            <div class="result-row">
              <div>Asthma Exacerbation<div class="bar"><b style="width:72%"></b></div></div>
              <span class="score">72%</span>
            </div>
            <div class="result-row">
              <div>Influenza<div class="bar"><b style="width:64%"></b></div></div>
              <span class="score">64%</span>
            </div>
          </div>
        </div>
      </section>
    </main>
  `;
}

function pageHead(kicker, title, text, action = '') {
  return `
    <div class="page-head">
      <div>
        <span class="kicker">${escapeHtml(kicker)}</span>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(text)}</p>
      </div>
      ${action}
    </div>
  `;
}

function overviewPage() {
  const stats = state.stats || {
    conditions: '--',
    symptoms: '--',
    risk_factors: '--',
    tests: '--',
    treatments: '--',
    evaluations: '--',
  };

  return `
    ${pageHead('Workspace', 'Clinical Decision Support', 'A clear view of the local knowledge base and decision-support workflow.', '<button class="pill" data-page="evaluate">New evaluation</button>')}

    <div class="content-grid">
      <section class="panel">
        <div class="section-head">
          <div>
            <h2>Start with a patient</h2>
            <p>Use stored symptoms and risk factors to create a transparent assessment.</p>
          </div>
        </div>
        <div class="notice">
          Results are software ranking signals based on stored relationships and weights. They are decision-support indicators and not medically validated probabilities.
        </div>
        <div class="form-actions" style="margin-top:20px; display:flex; gap:12px;">
          <button class="pill" data-page="evaluate">Open Evaluation</button>
          <button class="pill light" data-page="knowledge">Browse Knowledge Base</button>
        </div>
      </section>

      <aside class="panel">
        <h2>Knowledge base records</h2>
        <div class="info-list" style="margin-top:22px;">
          <div class="info-item"><span>Conditions</span><strong>${stats.conditions}</strong></div>
          <div class="info-item"><span>Symptoms</span><strong>${stats.symptoms}</strong></div>
          <div class="info-item"><span>Risk Factors</span><strong>${stats.risk_factors}</strong></div>
          <div class="info-item"><span>Tests</span><strong>${stats.tests}</strong></div>
          <div class="info-item"><span>Treatments</span><strong>${stats.treatments}</strong></div>
          <div class="info-item"><span>Saved Evaluations</span><strong>${stats.evaluations}</strong></div>
        </div>
      </aside>
    </div>
  `;
}

async function loadStats() {
  try {
    state.stats = await api('/stats');
    render();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

async function loadResource(type) {
  if (!type) return;
  state.loading = true;
  render();

  try {
    state.data[type] = await api(`/${type}`);
  } catch (error) {
    state.error = error.message;
  } finally {
    state.loading = false;
    render();
  }
}

function evaluationPage() {
  const symptoms = state.data.symptoms || [];
  const risks = state.data['risk-factors'] || [];
  const tests = state.data.tests || [];

  return `
    ${pageHead('Evaluation', 'Patient evaluation', 'Enter observed findings and clinical context for Bayesian diagnostic inference.')}
    ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ''}

    <div class="content-grid">
      <section class="panel">
        <form id="evaluation-form">
          <div class="form-section">
            <h3>Patient information</h3>
            <div class="field-grid">
              <label>Age<input name="age" type="number" min="0" max="130" placeholder="e.g. 58"></label>
              <label>Sex
                <select name="sex">
                  <option value="">Not specified</option>
                  <option>Female</option>
                  <option>Male</option>
                  <option>Other</option>
                </select>
              </label>
            </div>
          </div>

          <div class="form-section">
            <h3>Positive Symptoms (Observed Present)</h3>
            <p style="font-size:12px;color:var(--muted);">Select symptoms confirmed present in the patient.</p>
            ${selector('symptoms', state.selectedSymptoms, symptoms, 'Search symptoms...')}
          </div>

          <div class="form-section">
            <h3>Risk Factors</h3>
            ${selector('risk-factors', state.selectedRisks, risks, 'Search risk factors...')}
          </div>

          <div class="form-section">
            <h3>Confirmed Absent Symptoms (Explicit Negatives)</h3>
            <p style="font-size:12px;color:var(--muted);">Symptoms confirmed NOT present (e.g. ruled out chest pain). Unrecorded symptoms are preserved as neutral missing data.</p>
            ${selector('negative-symptoms', state.selectedNegativeSymptoms, symptoms, 'Add confirmed absent symptom...')}
          </div>

          <div class="form-section">
            <h3>Completed Diagnostic Tests</h3>
            <p style="font-size:12px;color:var(--muted);">Tests already completed (will be excluded from new recommendations).</p>
            ${selector('completed-tests', state.completedTests, tests, 'Add completed test to exclude...')}
          </div>

          <div class="form-actions">
            <button class="pill" type="submit">${state.loading ? 'Evaluating...' : 'Evaluate Patient (Bayesian)'}</button>
          </div>
        </form>
      </section>

      <aside class="panel">
        <h2>Inference &amp; Test Selection</h2>
        <div class="notice" style="margin-top:16px;">
          <strong>Bayesian Inference:</strong> Calculates posterior condition probabilities from documented priors and sensitivities. Unrecorded findings are not penalized as negatives.
        </div>
        <div class="notice" style="margin-top:12px;">
          <strong>Information Gain:</strong> Diagnostic tests are ranked by expected uncertainty reduction (entropy reduction) across competing candidates.
        </div>
        <div class="info-list" style="margin-top:22px;">
          <div class="info-item"><span>Symptoms available</span><strong>${symptoms.length}</strong></div>
          <div class="info-item"><span>Risk factors</span><strong>${risks.length}</strong></div>
          <div class="info-item"><span>Tests available</span><strong>${tests.length}</strong></div>
        </div>
      </aside>
    </div>
  `;
}

function suggestionMarkup(type, selected, values, query) {
  return values
    .filter((item) => item.name.toLowerCase().includes(query.toLowerCase()) && !selected.includes(item.name))
    .slice(0, 8)
    .map((item) => `<button type="button" class="suggestion" data-add="${type}" data-value="${escapeHtml(item.name)}">+ ${escapeHtml(item.name)}</button>`)
    .join('');
}

function bindAddButtons(root = document) {
  root.querySelectorAll('[data-add]').forEach((el) => {
    el.onclick = () => {
      const type = el.dataset.add;
      let key = 'selectedSymptoms';
      if (type === 'risk-factors') key = 'selectedRisks';
      else if (type === 'negative-symptoms') key = 'selectedNegativeSymptoms';
      else if (type === 'completed-tests') key = 'completedTests';
      const value = el.dataset.value;
      if (!state[key].includes(value)) {
        state[key].push(value);
      }
      render();
    };
  });
}

function selector(type, selected, values, placeholder) {
  let queryKey = 'symptomsQuery';
  if (type === 'risk-factors') queryKey = 'risksQuery';
  else if (type === 'negative-symptoms') queryKey = 'negativeSymptomsQuery';
  else if (type === 'completed-tests') queryKey = 'completedTestsQuery';
  const query = state[queryKey] || '';

  return `
    <div class="choice-box">
      ${selected.map((item) => `
        <span class="choice">${escapeHtml(item)}
          <button type="button" data-remove="${type}" data-value="${escapeHtml(item)}">&times;</button>
        </span>
      `).join('')}
      <input data-search="${type}" value="${escapeHtml(query)}" placeholder="${escapeHtml(placeholder)}">
    </div>
    <div class="suggestions" data-suggestions="${type}">${suggestionMarkup(type, selected, values, query)}</div>
  `;
}

async function submitEvaluation(event) {
  event.preventDefault();

  if (!state.selectedSymptoms.length) {
    state.error = 'Select at least one symptom to evaluate the patient.';
    render();
    return;
  }

  state.loading = true;
  state.error = '';
  render();

  const form = event.currentTarget;
  const formData = new FormData(form);
  const payload = {
    symptoms: state.selectedSymptoms,
    risk_factors: state.selectedRisks,
    negative_symptoms: state.selectedNegativeSymptoms || [],
    completed_tests: state.completedTests || [],
  };

  const age = formData.get('age');
  const sex = formData.get('sex');
  if (age) payload.age = Number(age);
  if (sex) payload.sex = sex;

  try {
    state.results = await api('/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.page = 'results';
    render();
  } catch (error) {
    state.error = error.message;
    render();
  } finally {
    state.loading = false;
  }
}

function resultsPage() {
  if (!state.results) {
    return `
      ${pageHead('Results', 'No evaluation yet', 'Run a patient evaluation to see ranked conditions and supporting factors.', '<button class="pill" data-page="evaluate">Start evaluation</button>')}
    `;
  }

  const rows = state.results.ranked_conditions || [];
  const diffTests = state.results.differential_tests || [];
  const entropy = state.results.diagnostic_entropy;

  return `
    ${pageHead('Results', 'Bayesian Diagnostic Assessment', 'Posterior condition probabilities and intelligent test recommendations based on expected information gain.', '<button class="pill" data-page="evaluate">New evaluation</button>')}
    
    <div class="notice" style="margin-bottom:20px;">
      ${escapeHtml(state.results.disclaimer || '')}
      ${entropy != null ? `<div style="margin-top:6px;font-size:12px;"><strong>Diagnostic Uncertainty (Entropy):</strong> ${entropy} bits</div>` : ''}
    </div>

    ${diffTests.length ? `
      <section class="panel" style="margin-bottom:24px;">
        <div class="section-head">
          <div>
            <h2>Intelligent Diagnostic Test Recommendations</h2>
            <p>Ranked by Expected Information Gain (uncertainty reduction) across competing candidate conditions.</p>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;margin-top:14px;">
          ${diffTests.map(t => `
            <div style="padding:14px;border:1px solid var(--line);border-radius:8px;background:var(--surface);">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                <strong style="font-size:14px;">${escapeHtml(t.name)}</strong>
                <span class="pill small" style="background:var(--green-light);color:var(--green-deep);font-size:11px;font-weight:600;padding:2px 8px;">
                  ${t.is_information_gain_calculated && t.information_gain != null ? `${t.information_gain} bits Info Gain` : 'Priority ' + t.priority}
                </span>
              </div>
              <p style="margin:6px 0;font-size:12px;color:var(--muted);">${escapeHtml(t.purpose || t.description || '')}</p>
              ${t.discriminates_between && t.discriminates_between.length ? `
                <div style="font-size:11px;color:var(--text);margin-top:6px;"><strong>Investigates:</strong> ${escapeHtml(t.discriminates_between.join(', '))}</div>
              ` : ''}
              ${t.rationale ? `<div style="font-size:11px;color:var(--muted);margin-top:4px;">${escapeHtml(t.rationale)}</div>` : ''}
              ${t.missing_parameters ? '<div style="font-size:10px;color:var(--accent-orange);margin-top:4px;">Sensitivity/specificity unrecorded; ranked by relational priority.</div>' : ''}
            </div>
          `).join('')}
        </div>
      </section>
    ` : ''}

    <div class="results-list">
      ${rows.length ? rows.map((item, index) => resultCard(item, index)).join('') : '<div class="panel empty">No candidate conditions matched the submitted findings.</div>'}
    </div>
  `;
}

function addRecordsPage() {
  const config = resourceConfig[state.addType] || resourceConfig.conditions;
  const fields = state.addType === 'conditions'
    ? `
        <div class="field-grid">
          <label>Name<input name="name" required placeholder="e.g. Pneumonia"></label>
          <label>Description<textarea name="description" placeholder="Describe this condition"></textarea></label>
          <label>Severity (1-10)<input name="severity" type="number" min="1" max="10" required value="5"></label>
          <label>Urgency (1-10)<input name="urgency" type="number" min="1" max="10" required value="5"></label>
        </div>`
    : `
        <label>Name<input name="name" required placeholder="Enter a ${escapeHtml(config.singular)} name"></label>
        <label>Description<textarea name="description" placeholder="Add an optional description"></textarea></label>
        ${state.addType === 'risk-factors' ? '<label>Factor type<input name="factor_type" required placeholder="e.g. lifestyle"></label>' : ''}
        ${state.addType === 'tests' ? '<label>Purpose<textarea name="purpose" placeholder="What is this test used for?"></textarea></label>' : ''}
        ${state.addType === 'treatments' ? '<label>Treatment type<input name="treatment_type" required placeholder="e.g. medication"></label>' : ''}`;

  return `
    ${pageHead('Knowledge base', 'Add new records', 'Create new clinical entries that can be used in evaluations and shown in the knowledge base.')}
    <div class="kb-tabs">
      ${Object.entries(resourceConfig).map(([key, value]) => `<button class="tab ${key === state.addType ? 'active' : ''}" data-add-type="${key}">${value.label}</button>`).join('')}
    </div>
    <section class="panel add-record-panel">
      <h2>New ${config.singular}</h2>
      <p>Required fields are marked by the browser before submission.</p>
      ${state.addError ? `<div class="error">${escapeHtml(state.addError)}</div>` : ''}
      <form id="add-record-form" class="form-stack">
        ${fields}
        <div class="form-actions">
          <button class="pill" type="submit" ${state.addLoading ? 'disabled' : ''}>${state.addLoading ? 'Saving...' : `Save ${config.singular}`}</button>
        </div>
      </form>
    </section>
  `;
}

async function submitNewRecord(event) {
  event.preventDefault();
  state.addLoading = true;
  state.addError = '';
  render();

  const formData = new FormData(event.currentTarget);
  const payload = Object.fromEntries(formData.entries());
  if (state.addType === 'conditions') {
    payload.severity = Number(payload.severity);
    payload.urgency = Number(payload.urgency);
  }

  try {
    await api(`/${state.addType}`, { method: 'POST', body: JSON.stringify(payload) });
    state.data[state.addType] = await api(`/${state.addType}`);
    state.stats = await api('/stats');
    toast(`${resourceConfig[state.addType].singular} saved successfully.`);
  } catch (error) {
    state.addError = error.message;
  } finally {
    state.addLoading = false;
    render();
  }
}

function resultCard(item, index) {
  const prob = item.posterior_probability != null ? item.posterior_probability : item.likelihood_score;
  const percentage = Math.round((prob || 0) * 100);
  const probLabel = item.is_probability ? 'Posterior Prob (Bayesian)' : 'Heuristic Score';

  const detail = `
    <div class="condition-detail">
      <div>
        <h4>Matched symptoms (Observed)</h4>
        <ul class="detail-list">${(item.matched_symptoms || []).map((s) => `<li>${escapeHtml(s.name)} <small style="color:var(--muted);">(weight: ${s.weight}${s.probability != null ? `, P=${s.probability.toFixed(2)}` : ''})</small></li>`).join('') || '<li>None matched</li>'}</ul>
      </div>
      <div>
        <h4>Matched risk factors</h4>
        <ul class="detail-list">${(item.matched_risk_factors || []).map((s) => `<li>${escapeHtml(s.name)} <small style="color:var(--muted);">(weight: ${s.weight})</small></li>`).join('') || '<li>None matched</li>'}</ul>
      </div>
      ${item.absent_symptoms && item.absent_symptoms.length ? `
        <div>
          <h4>Confirmed Absent Symptoms</h4>
          <ul class="detail-list">${item.absent_symptoms.map(s => `<li>${escapeHtml(s.name)} (Excluded)</li>`).join('')}</ul>
        </div>
      ` : ''}
      <div>
        <h4>Recommended Diagnostic Tests</h4>
        <ul class="detail-list">
          ${(item.recommended_tests || []).map((test) => `
            <li>
              <strong>${escapeHtml(test.name)}</strong>
              ${test.is_information_gain_calculated && test.information_gain != null ? `<span class="pill small" style="margin-left:6px;font-size:10px;background:var(--green-light);color:var(--green-deep);">${test.information_gain} bits Info Gain</span>` : `<span class="pill small" style="margin-left:6px;font-size:10px;">Priority ${test.priority}</span>`}
              ${test.purpose ? `<br><small style="color:var(--muted);">${escapeHtml(test.purpose)}</small>` : ''}
              ${test.rationale ? `<br><small style="color:var(--text);">${escapeHtml(test.rationale)}</small>` : ''}
            </li>
          `).join('') || '<li>None stored</li>'}
        </ul>
      </div>
      <div>
        <h4>Potential Treatments</h4>
        <ul class="detail-list">${(item.treatments || []).map((tx) => `<li><strong>${escapeHtml(tx.name)}</strong> (Priority ${tx.priority})${tx.notes ? `<br><small style="color:var(--muted);">${escapeHtml(tx.notes)}</small>` : ''}</li>`).join('') || '<li>None stored</li>'}</ul>
      </div>
      ${item.explanation ? `
        <div style="grid-column: 1 / -1; margin-top: 10px; padding: 12px; background: var(--surface); border-radius: 6px; font-size: 12px; border: 1px solid var(--line);">
          <strong>Inference Explanation:</strong> ${escapeHtml(item.explanation)}
        </div>
      ` : ''}
    </div>
  `;

  return `
    <article class="condition-card">
      <div class="condition-summary" data-expand="${index}">
        <div>
          <h3>${escapeHtml(item.condition)}</h3>
          <small>Clinical Triage Priority: ${item.priority_score}</small>
        </div>
        <div class="metric"><span>${probLabel}</span><strong>${percentage}%</strong></div>
        <div class="metric"><span>Severity</span><strong>${item.severity || '—'}/10</strong></div>
        <div class="metric"><span>Urgency</span><strong>${item.urgency || '—'}/10</strong></div>
      </div>
      ${detail}
    </article>
  `;
}

function knowledgePage(type = 'conditions') {
  const config = resourceConfig[type] || resourceConfig.conditions;
  const records = state.data[type] || [];
  const query = state.kbQuery || '';
  const filtered = records.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()));

  return `
    ${pageHead('Knowledge base', config.label, 'Review the clinical resources available in the database.', '<button class="pill" data-page="evaluate">New evaluation</button>')}

    <div class="kb-tabs">
      ${Object.entries(resourceConfig).map(([key, value]) => `<button class="tab ${key === type ? 'active' : ''}" data-page="knowledge:${key}">${value.label}</button>`).join('')}
    </div>

    <section class="panel">
      <div class="toolbar">
        <input id="kb-search" value="${escapeHtml(query)}" placeholder="Search ${escapeHtml(config.label.toLowerCase())}...">
      </div>

      ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ''}
      ${state.loading ? '<div class="loading">Loading records...</div>' : ''}

      <div class="table-wrap" data-kb-table style="${state.error || state.loading || !filtered.length ? 'display:none;' : ''}">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>${type === 'conditions' ? 'Severity / Urgency' : type === 'risk-factors' ? 'Factor Type' : type === 'tests' ? 'Purpose' : 'Info'}</th>
            </tr>
          </thead>
          <tbody>
            ${records.map((item) => `
              <tr data-kb-row data-search-name="${escapeHtml(item.name.toLowerCase())}" style="${item.name.toLowerCase().includes(query.toLowerCase()) ? '' : 'display:none;'}">
                <td><strong>${escapeHtml(item.name)}</strong></td>
                <td>${escapeHtml(item.description || 'No description provided')}</td>
                <td>
                  ${type === 'conditions'
                    ? `${item.severity ?? '—'} / ${item.urgency ?? '—'}`
                    : escapeHtml(item.type || item.purpose || item.treatment_type || '—')}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div class="empty" data-kb-empty style="${state.error || state.loading || filtered.length ? 'display:none;' : ''}">
        ${records.length ? 'No matching records found.' : 'No records found in this category.'}
      </div>
    </section>
  `;
}

function toast(message) {
  document.body.insertAdjacentHTML('beforeend', `<div class="toast">${escapeHtml(message)}</div>`);
  setTimeout(() => document.querySelector('.toast')?.remove(), 3000);
}

function bindEvents() {
  document.querySelectorAll('[data-page]').forEach((el) => {
    el.onclick = (event) => {
      event.preventDefault();
      const page = el.dataset.page;
      if (page === 'home') {
        state.page = 'home';
        render();
        return;
      }

      state.page = page;
      if (page === 'overview') {
        loadStats();
      }
      if (page === 'evaluate') {
        if (!state.data.symptoms.length) {
          loadResource('symptoms');
        }
        if (!state.data['risk-factors'].length) {
          loadResource('risk-factors');
        }
      }
      if (page.startsWith('knowledge:')) {
        const key = page.split(':')[1] || 'conditions';
        if (!state.data[key]) {
          loadResource(key);
        }
      }
      render();
    };
  });

  document.querySelector('#evaluation-form')?.addEventListener('submit', submitEvaluation);
  document.querySelector('#add-record-form')?.addEventListener('submit', submitNewRecord);

  document.querySelectorAll('[data-add-type]').forEach((el) => {
    el.onclick = () => {
      state.addType = el.dataset.addType;
      state.addError = '';
      render();
    };
  });

  bindAddButtons();

  document.querySelectorAll('[data-remove]').forEach((el) => {
    el.onclick = () => {
      const type = el.dataset.remove;
      let key = 'selectedSymptoms';
      if (type === 'risk-factors') key = 'selectedRisks';
      else if (type === 'negative-symptoms') key = 'selectedNegativeSymptoms';
      else if (type === 'completed-tests') key = 'completedTests';
      const value = el.dataset.value;
      state[key] = state[key].filter((item) => item !== value);
      render();
    };
  });

  document.querySelectorAll('[data-search]').forEach((el) => {
    el.oninput = (event) => {
      const type = event.target.dataset.search;
      let key = 'symptomsQuery';
      let selectedKey = 'selectedSymptoms';
      let dataKey = 'symptoms';
      if (type === 'risk-factors') {
        key = 'risksQuery';
        selectedKey = 'selectedRisks';
        dataKey = 'risk-factors';
      } else if (type === 'negative-symptoms') {
        key = 'negativeSymptomsQuery';
        selectedKey = 'selectedNegativeSymptoms';
        dataKey = 'symptoms';
      } else if (type === 'completed-tests') {
        key = 'completedTestsQuery';
        selectedKey = 'completedTests';
        dataKey = 'tests';
      }
      state[key] = event.target.value;
      const suggestions = document.querySelector(`[data-suggestions="${type}"]`);
      if (suggestions) {
        suggestions.innerHTML = suggestionMarkup(type, state[selectedKey], state.data[dataKey] || [], state[key]);
        bindAddButtons(suggestions);
      }
    };
  });

  document.querySelector('#kb-search')?.addEventListener('input', (event) => {
    state.kbQuery = event.target.value;
    const table = document.querySelector('[data-kb-table]');
    const empty = document.querySelector('[data-kb-empty]');
    if (!table || !empty || document.querySelector('.panel .error, .panel .loading')) return;

    const query = state.kbQuery.toLowerCase();
    const rows = table.querySelectorAll('[data-kb-row]');
    let visibleCount = 0;
    rows.forEach((row) => {
      const visible = row.dataset.searchName.includes(query);
      row.style.display = visible ? '' : 'none';
      if (visible) visibleCount += 1;
    });

    table.style.display = visibleCount ? '' : 'none';
    empty.style.display = visibleCount ? 'none' : '';
    empty.textContent = rows.length ? 'No matching records found.' : 'No records found in this category.';
  });
}

async function init() {
  try {
    state.data.symptoms = await api('/symptoms');
    state.data['risk-factors'] = await api('/risk-factors');
    state.data.tests = await api('/tests');
    state.stats = await api('/stats');
  } catch (error) {
    state.error = error.message;
  }
  render();
}

init();

