const API_BASE = window.CDSS_API_URL || (window.location.origin.includes(':8000') ? '' : 'http://127.0.0.1:8000');

const resourceConfig = {
  conditions: { label: 'Conditions', singular: 'condition', fields: ['name', 'description', 'severity', 'urgency'] },
  symptoms: { label: 'Symptoms', singular: 'symptom', fields: ['name', 'description'] },
  'risk-factors': { label: 'Risk Factors', singular: 'risk factor', fields: ['name', 'description', 'factor_type'] },
  tests: { label: 'Tests', singular: 'test', fields: ['name', 'description', 'purpose'] },
  treatments: { label: 'Treatments', singular: 'treatment', fields: ['name', 'description', 'treatment_type'] },
};

const state = {
  page: 'home',
  data: {},
  stats: null,
  selectedSymptoms: [],
  selectedRisks: [],
  results: null,
  lastInput: null,
  savedRecordId: null,
  evaluations: [],
  expanded: 0,
  loading: false,
  error: '',
  kbQuery: '',
  symptomsQuery: '',
  risksQuery: '',
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
      /* use safe fallback */
    }
    throw new Error(message);
  }
  return response.json();
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function go(page) {
  state.page = page;
  state.error = '';
  render();
  if (page === 'overview') loadStats();
  if (page === 'evaluate') loadOptions();
  if (page === 'records') loadEvaluations();
  if (page === 'knowledge' || page.startsWith('knowledge:')) {
    loadResource(page.split(':')[1] || 'conditions');
  }
}

function render() {
  app.innerHTML = state.page === 'home' ? landing() : application();
  bindEvents();
}

function landing() {
  return `
  <header class="app-header">
    <a class="brand" href="#"><span class="brand-mark"></span>clarity<span style="color:var(--green-deep)">.</span></a>
    <nav class="top-nav">
      <a href="#overview" data-page="overview">Workspace</a>
      <a href="#knowledge" data-page="knowledge">Knowledge Base</a>
      <a href="#evaluate" data-page="evaluate">Evaluate</a>
    </nav>
    <div class="header-actions">
      <button class="pill" data-page="overview">Open Workspace</button>
    </div>
  </header>
  <main class="landing">
    <section class="hero">
      <div>
        <span class="eyebrow">Clinical decision support</span>
        <h1>Make clinical decisions with greater clarity.</h1>
        <p class="hero-copy">Analyze patient symptoms and risk factors to identify candidate conditions, prioritize urgency, and explore relevant diagnostic tests and treatments backed by a normalized database.</p>
        <div class="hero-actions">
          <button class="pill" data-page="evaluate">Start Evaluation</button>
          <button class="pill light" data-page="knowledge">Explore Knowledge Base</button>
        </div>
        <div class="trust"><i></i> Connected to local database with live knowledge base querying</div>
      </div>
      ${heroMockup()}
    </section>
  </main>`;
}

function heroMockup() {
  return `
  <div class="mockup">
    <div class="mockup-top">
      <div><span class="kicker">Live assessment</span><h3>Clinical CDSS</h3></div>
      <span class="status">System Online</span>
    </div>
    <div class="mock-label">Common Stored Symptoms</div>
    <div class="tags">
      <span class="tag">Fever</span><span class="tag">Cough</span><span class="tag">Shortness of breath</span>
    </div>
    <div class="mock-label">Diagnostic Knowledge Base</div>
    <div class="mock-results">
      <div class="result-row"><div>Pneumonia<div class="bar"><b style="width:85%"></b></div></div><span class="score">85%</span></div>
      <div class="result-row"><div>Asthma Exacerbation<div class="bar"><b style="width:72%"></b></div></div><span class="score">72%</span></div>
      <div class="result-row"><div>Influenza<div class="bar"><b style="width:64%"></b></div></div><span class="score">64%</span></div>
    </div>
    <div class="mock-footer">
      <div class="mini-stat">Status<strong>Connected</strong></div>
      <div class="mini-stat">Database<strong>SQLite</strong></div>
      <div class="mini-stat">API<strong>FastAPI</strong></div>
    </div>
  </div>`;
}

function application() {
  const mobile = `<button class="mobile-menu" id="menu-button" aria-label="Open navigation">☰</button>`;
  return `
  <div class="app-shell">
    <aside class="sidebar" id="sidebar">
      <a class="brand" href="#" data-page="home"><span class="brand-mark"></span>clarity<span style="color:var(--green-deep)">.</span></a>
      <div class="side-label">Workspace</div>
      <nav class="side-nav">
        ${navButton('overview', 'Overview')}
        ${navButton('evaluate', 'Patient Evaluation')}
        ${navButton('results', 'Results')}
        ${navButton('records', 'Patient Records')}
      </nav>
      <div class="side-label" style="margin-top:27px">Knowledge Base</div>
      <nav class="side-nav">
        ${navButton('knowledge', 'All Knowledge')}
        ${Object.entries(resourceConfig).map(([key, config]) => navButton(`knowledge:${key}`, config.label)).join('')}
      </nav>
      <div class="sidebar-bottom">
        <div style="padding: 12px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--line);">
          <div>Backend: <span style="color:var(--green-deep);font-weight:600;">Connected</span></div>
          <div style="margin-top:4px;">Endpoint: ${API_BASE || 'Same Origin'}</div>
        </div>
      </div>
    </aside>
    <main class="main">
      ${mobile}
      ${pageContent()}
    </main>
  </div>`;
}

function navButton(page, label) {
  const active = state.page === page || (state.page.startsWith('knowledge') && page === 'knowledge' && !state.page.includes(':')) || (state.page === page);
  return `<button class="${active ? 'active' : ''}" data-page="${page}">${label}</button>`;
}

function pageContent() {
  if (state.page === 'evaluate') return evaluationPage();
  if (state.page === 'results') return resultsPage();
  if (state.page === 'records') return recordsPage();
  if (state.page.startsWith('knowledge')) return knowledgePage(state.page.split(':')[1] || 'conditions');
  return overviewPage();
}

function pageHead(kicker, title, text, action = '') {
  return `<div class="page-head"><div><span class="kicker">${kicker}</span><h1>${title}</h1><p>${text}</p></div>${action}</div>`;
}

async function loadStats() {
  try {
    state.stats = await api('/stats');
    render();
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

async function triggerSeed() {
  state.loading = true;
  state.error = '';
  render();
  try {
    const res = await api('/seed-demo', { method: 'POST' });
    toast(res.message || 'Clinical data seeded successfully!');
    state.data = {};
    await loadStats();
  } catch (err) {
    toast(err.message);
  } finally {
    state.loading = false;
    render();
  }
}

function overviewPage() {
  const stats = state.stats || { conditions: '--', symptoms: '--', risk_factors: '--', tests: '--', treatments: '--', evaluations: '--' };
  return `
  ${pageHead('Workspace', 'Clinical Decision Support', 'A clear view of your decision-support workspace, database records, and active knowledge base.', '<button class="pill" data-page="evaluate">New evaluation</button>')}
  
  <div class="overview-status-card">
    <div class="overview-status-left">
      <span class="status-pill dot">Database Connected</span>
      <span>Live local clinical database is ready.</span>
    </div>
    <div>
      <button class="pill small outline" id="btn-seed-data">${state.loading ? 'Seeding...' : 'Load Sample Medical Knowledge'}</button>
    </div>
  </div>

  <div class="content-grid">
    <section class="panel">
      <div class="section-head">
        <div>
          <h2>Start with a patient</h2>
          <p>Use stored symptoms and risk factors to create an explainable assessment.</p>
        </div>
      </div>
      <div class="notice">
        Results are transparent software ranking signals computed from relationships and weights explicitly stored in the knowledge base. They are physician-support indicators and not medically validated probabilities.
      </div>
      <div class="form-actions" style="margin-top:20px;display:flex;gap:12px;">
        <button class="pill" data-page="evaluate">Open Evaluation</button>
        <button class="pill light" data-page="records">View Patient Records</button>
      </div>
    </section>

    <aside class="panel">
      <h2>Knowledge base records</h2>
      <p>Live database inventory</p>
      <div class="info-list" style="margin-top:22px">
        <div class="info-item"><span>Conditions</span><strong>${stats.conditions}</strong></div>
        <div class="info-item"><span>Symptoms</span><strong>${stats.symptoms}</strong></div>
        <div class="info-item"><span>Risk Factors</span><strong>${stats.risk_factors}</strong></div>
        <div class="info-item"><span>Diagnostic Tests</span><strong>${stats.tests}</strong></div>
        <div class="info-item"><span>Treatments</span><strong>${stats.treatments}</strong></div>
        <div class="info-item"><span>Saved Patient Records</span><strong>${stats.evaluations}</strong></div>
      </div>
    </aside>
  </div>`;
}

function optionData(type) {
  return state.data[type] || [];
}

async function loadOptions() {
  for (const type of ['symptoms', 'risk-factors']) {
    if (!state.data[type]) {
      try {
        state.data[type] = await api(`/${type}`);
        render();
      } catch (error) {
        state.error = error.message;
        render();
      }
    }
  }
}

function evaluationPage() {
  const symptoms = optionData('symptoms');
  const risks = optionData('risk-factors');
  return `
  ${pageHead('Evaluation', 'Patient evaluation', 'Enter symptoms and relevant risk factors to generate a clinical decision-support assessment.')}
  ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ''}
  <div class="content-grid">
    <section class="panel">
      <form id="evaluation-form">
        <div class="form-section">
          <h3>Patient information</h3>
          <p>Optional demographics context saved with the assessment.</p>
          <div class="field-grid">
            <label>Age<input name="age" type="number" min="0" max="130" placeholder="e.g. 58" value="${state.lastInput?.age || ''}"></label>
            <label>Sex
              <select name="sex">
                <option value="">Not specified</option>
                <option ${state.lastInput?.sex === 'Female' ? 'selected' : ''}>Female</option>
                <option ${state.lastInput?.sex === 'Male' ? 'selected' : ''}>Male</option>
                <option ${state.lastInput?.sex === 'Other' ? 'selected' : ''}>Other</option>
              </select>
            </label>
          </div>
        </div>
        <div class="form-section">
          <h3>Symptoms</h3>
          <p>Select symptoms presented by the patient (matched against database).</p>
          ${selector('symptoms', state.selectedSymptoms, symptoms, 'Type to search symptoms...')}
        </div>
        <div class="form-section">
          <h3>Risk factors</h3>
          <p>Select relevant risk factors from the knowledge base.</p>
          ${selector('risk-factors', state.selectedRisks, risks, 'Type to search risk factors...')}
        </div>
        <div class="form-actions">
          <button class="pill" id="evaluate-button" type="submit">${state.loading ? 'Evaluating...' : 'Evaluate Patient'}</button>
        </div>
      </form>
    </section>

    <aside class="panel">
      <h2>Knowledge base status</h2>
      <p>Loaded clinical resources</p>
      <div class="notice" style="margin-top:20px">
        Selecting symptoms matches condition relationships and ranks candidate diagnoses with diagnostic tests and treatments.
      </div>
      <div class="info-list" style="margin-top:23px">
        <div class="info-item"><span>Symptoms available</span><strong>${symptoms.length}</strong></div>
        <div class="info-item"><span>Risk factors available</span><strong>${risks.length}</strong></div>
      </div>
      <div style="margin-top:20px;">
        <button class="pill small light" data-page="knowledge" style="width:100%;">Explore Knowledge Base</button>
      </div>
    </aside>
  </div>`;
}

function selector(type, selected, values, placeholder) {
  const queryKey = type === 'symptoms' ? 'symptomsQuery' : 'risksQuery';
  const query = state[queryKey] || '';
  const filtered = values
    .filter(item => item.name.toLowerCase().includes(query.toLowerCase()) && !selected.includes(item.name))
    .slice(0, 10);

  return `
  <div class="choice-box">
    ${selected.map(item => `<span class="choice">${escapeHtml(item)}<button type="button" data-remove="${type}" data-value="${escapeHtml(item)}">&times;</button></span>`).join('')}
    <input data-search="${type}" value="${escapeHtml(query)}" placeholder="${placeholder}">
  </div>
  <div class="suggestions">
    ${filtered.map(item => `<button type="button" class="suggestion" data-add="${type}" data-value="${escapeHtml(item.name)}">+ ${escapeHtml(item.name)}</button>`).join('')}
  </div>`;
}

async function submitEvaluation(form) {
  const formData = new FormData(form);
  if (!state.selectedSymptoms.length) {
    state.error = 'Select at least one symptom to evaluate the patient.';
    render();
    return;
  }
  state.loading = true;
  state.error = '';
  render();

  const demographics = {};
  const ageVal = formData.get('age');
  if (ageVal) demographics.age = Number(ageVal);
  const sexVal = formData.get('sex');
  if (sexVal) demographics.sex = sexVal;

  state.lastInput = {
    age: ageVal ? Number(ageVal) : null,
    sex: sexVal || null,
    symptoms: [...state.selectedSymptoms],
    risk_factors: [...state.selectedRisks],
  };
  state.savedRecordId = null;

  try {
    state.results = await api('/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        symptoms: state.selectedSymptoms,
        risk_factors: state.selectedRisks,
        demographics,
      }),
    });
    state.page = 'results';
  } catch (error) {
    state.error = error.message;
  } finally {
    state.loading = false;
    render();
  }
}

function resultsPage() {
  if (!state.results) {
    return `
    ${pageHead('Results', 'No evaluation yet', 'Run a patient evaluation to see ranked conditions and supporting factors.', '<button class="pill" data-page="evaluate">Start evaluation</button>')}
    `;
  }

  const hasConditions = state.results.ranked_conditions && state.results.ranked_conditions.length > 0;
  const saveBtn = state.savedRecordId
    ? `<button class="pill small success" disabled>Saved to Records (#${state.savedRecordId})</button>`
    : `<button class="pill small green" id="btn-save-record">Save to Patient Records</button>`;

  return `
  ${pageHead('Results', 'Evaluation assessment', 'Candidate conditions ranked by stored weighted relationships and severity.', `
    <div style="display:flex;gap:10px;">
      ${saveBtn}
      <button class="pill small light" data-page="evaluate">New evaluation</button>
    </div>
  `)}
  <div class="notice" style="margin-bottom:20px">${escapeHtml(state.results.disclaimer)}</div>
  <div class="results-list">
    ${hasConditions
      ? state.results.ranked_conditions.map((condition, index) => resultCard(condition, index)).join('')
      : '<div class="panel empty">No conditions in the database matched the submitted symptoms.</div>'}
  </div>`;
}

function resultCard(item, index) {
  const percent = Math.round(item.likelihood_score * 100);
  const detail = state.expanded === index ? `
  <div class="condition-detail">
    <div>
      <h4>Matched symptoms</h4>
      <ul class="detail-list">${factorList(item.matched_symptoms)}</ul>
    </div>
    <div>
      <h4>Matched risk factors</h4>
      <ul class="detail-list">${factorList(item.matched_risk_factors)}</ul>
    </div>
    <div>
      <h4>Recommended tests</h4>
      <ul class="detail-list">
        ${item.recommended_tests.length ? item.recommended_tests.map(test => `<li><strong>${escapeHtml(test.name)}</strong> (Priority ${test.priority})${test.purpose ? `<br><small class="muted-text">${escapeHtml(test.purpose)}</small>` : ''}</li>`).join('') : '<li>None stored</li>'}
      </ul>
      <h4 style="margin-top:16px;">Potential treatments</h4>
      <ul class="detail-list">
        ${item.treatments.length ? item.treatments.map(tx => `<li><strong>${escapeHtml(tx.name)}</strong> (Priority ${tx.priority})${tx.notes ? `<br><small class="muted-text">${escapeHtml(tx.notes)}</small>` : ''}</li>`).join('') : '<li>None stored</li>'}
      </ul>
    </div>
    <div class="explanation">${escapeHtml(item.explanation)}</div>
  </div>` : '';

  return `
  <article class="condition-card">
    <div class="condition-summary" data-expand="${index}">
      <div>
        <h3>${escapeHtml(item.condition)}</h3>
        <small>Priority Score: ${item.priority_score}</small>
      </div>
      <div class="metric">
        <span>Likelihood</span>
        <strong>${percent}%</strong>
      </div>
      <div class="metric">
        <span>Severity</span>
        <strong>${item.severity}/10</strong>
      </div>
      <div class="metric">
        <span>Urgency</span>
        <strong>${item.urgency}/10</strong>
      </div>
      <span class="chevron">${state.expanded === index ? '−' : '+'}</span>
    </div>
    ${detail}
  </article>`;
}

function factorList(factors) {
  return factors.length
    ? factors.map(factor => `<li>${escapeHtml(factor.name)} <small style="display:inline;color:var(--muted)">weight: ${factor.weight}</small></li>`).join('')
    : '<li>None matched</li>';
}

async function saveCurrentEvaluation() {
  if (!state.results || !state.lastInput) return;
  const topCond = state.results.ranked_conditions?.[0];
  const payload = {
    age: state.lastInput.age,
    sex: state.lastInput.sex,
    symptoms: state.lastInput.symptoms,
    risk_factors: state.lastInput.risk_factors,
    top_condition: topCond ? topCond.condition : null,
    likelihood_score: topCond ? topCond.likelihood_score : null,
    priority_score: topCond ? topCond.priority_score : null,
    results_json: JSON.stringify(state.results),
  };

  try {
    const saved = await api('/evaluations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.savedRecordId = saved.id;
    toast(`Assessment saved to Patient Records (#${saved.id})`);
    render();
  } catch (err) {
    toast(`Failed to save: ${err.message}`);
  }
}

async function loadEvaluations() {
  state.loading = true;
  render();
  try {
    state.evaluations = await api('/evaluations');
  } catch (err) {
    state.error = err.message;
  } finally {
    state.loading = false;
    render();
  }
}

function recordsPage() {
  return `
  ${pageHead('Patient Records', 'Evaluation History', 'Retrieve and review previous clinical patient assessments stored in the database.', '<button class="pill" data-page="evaluate">New evaluation</button>')}
  ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ''}
  <section class="panel">
    ${state.loading ? '<div class="loading">Loading patient records...</div>' : state.evaluations.length ? `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date / Time</th>
              <th>Patient</th>
              <th>Symptoms & Risk Factors</th>
              <th>Top Ranked Condition</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${state.evaluations.map(rec => `
              <tr>
                <td><strong>#${rec.id}</strong><small>${escapeHtml(rec.created_at)}</small></td>
                <td>${rec.age ? `Age ${rec.age}` : 'Age --'}<br><small>${escapeHtml(rec.sex || 'Not specified')}</small></td>
                <td>
                  <div>${rec.symptoms.map(s => `<span class="tag" style="margin:2px;">${escapeHtml(s)}</span>`).join('')}</div>
                  ${rec.risk_factors && rec.risk_factors.length ? `<div style="margin-top:4px;"><small class="muted-text">Risks: ${rec.risk_factors.map(r => escapeHtml(r)).join(', ')}</small></div>` : ''}
                </td>
                <td>
                  ${rec.top_condition ? `<strong>${escapeHtml(rec.top_condition)}</strong><br><small>Score: ${rec.likelihood_score != null ? Math.round(rec.likelihood_score * 100) + '%' : '--'}</small>` : '<span class="muted-text">No condition matched</span>'}
                </td>
                <td>
                  <button class="pill small outline btn-view-rec" data-rec-id="${rec.id}">View Results</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    ` : '<div class="empty">No patient evaluation records found in database. Run an evaluation and click "Save to Patient Records".</div>'}
  </section>`;
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

function knowledgePage(type) {
  const config = resourceConfig[type] || resourceConfig.conditions;
  const records = optionData(type);
  const query = state.kbQuery || '';
  const filtered = records.filter(item => item.name.toLowerCase().includes(query.toLowerCase()));

  return `
  ${pageHead('Knowledge base', config.label, 'Review and manage the clinical resources stored in the database.', `
    <div style="display:flex;gap:10px;">
      <button class="pill" data-add-resource="${type}">Add ${config.singular}</button>
    </div>
  `)}
  <div class="kb-tabs">
    ${Object.entries(resourceConfig).map(([key, value]) => `<button class="tab ${key === type ? 'active' : ''}" data-page="knowledge:${key}">${value.label}</button>`).join('')}
  </div>
  <section class="panel">
    <div class="toolbar">
      <input id="kb-search" placeholder="Search ${config.label.toLowerCase()}..." value="${escapeHtml(query)}">
    </div>
    ${state.error ? `<div class="error">${escapeHtml(state.error)}</div>` : ''}
    ${state.loading ? '<div class="loading">Loading database records...</div>' : filtered.length ? `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>${type === 'conditions' ? 'Severity / Urgency' : type === 'risk-factors' ? 'Factor Type' : type === 'tests' ? 'Purpose' : type === 'treatments' ? 'Treatment Type' : 'Info'}</th>
              ${type === 'conditions' ? '<th>Relationships</th>' : ''}
            </tr>
          </thead>
          <tbody>
            ${filtered.map(item => `
              <tr>
                <td><strong>${escapeHtml(item.name)}</strong><small>#${item.id}</small></td>
                <td>${escapeHtml(item.description || 'No description provided')}</td>
                <td>${type === 'conditions' ? `${item.severity != null ? item.severity : '—'} / ${item.urgency != null ? item.urgency : '—'}` : escapeHtml(item.purpose || item.type || '—')}</td>
                ${type === 'conditions' ? `
                  <td>
                    <button class="pill small outline btn-cond-detail" data-cond-id="${item.id}">View Details &amp; Links</button>
                  </td>
                ` : ''}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    ` : '<div class="empty">No records found in database for this category. Click "Add ' + config.singular + '" or load sample data from Overview.</div>'}
  </section>`;
}

async function openConditionDetails(conditionId) {
  try {
    const cond = await api(`/conditions/${conditionId}/details`);
    renderConditionModal(cond);
  } catch (err) {
    toast(`Failed to load condition details: ${err.message}`);
  }
}

function renderConditionModal(cond) {
  document.querySelector('#condition-detail-modal')?.remove();
  const symptomsList = cond.symptoms.length
    ? cond.symptoms.map(s => `<span class="tag-pill">${escapeHtml(s.name)} <strong>(weight: ${s.weight})</strong></span>`).join('')
    : '<span class="muted-text">No symptoms linked yet.</span>';

  const risksList = cond.risk_factors.length
    ? cond.risk_factors.map(r => `<span class="tag-pill">${escapeHtml(r.name)} <strong>(weight: ${r.weight})</strong></span>`).join('')
    : '<span class="muted-text">No risk factors linked yet.</span>';

  const testsList = cond.tests.length
    ? cond.tests.map(t => `<div class="tag-pill test" style="display:block;margin-bottom:6px;"><strong>[Priority ${t.priority}] ${escapeHtml(t.name)}</strong>${t.purpose ? `<br><small>${escapeHtml(t.purpose)}</small>` : ''}</div>`).join('')
    : '<span class="muted-text">No tests linked yet.</span>';

  const txList = cond.treatments.length
    ? cond.treatments.map(t => `<div class="tag-pill tx" style="display:block;margin-bottom:6px;"><strong>[Priority ${t.priority}] ${escapeHtml(t.name)}</strong>${t.notes ? `<br><small>${escapeHtml(t.notes)}</small>` : ''}</div>`).join('')
    : '<span class="muted-text">No treatments linked yet.</span>';

  const modalHtml = `
  <div class="modal-backdrop" id="condition-detail-modal">
    <div class="modal wide">
      <header>
        <div>
          <h2>${escapeHtml(cond.name)}</h2>
          <small class="muted-text">Severity: ${cond.severity}/10 &bull; Urgency: ${cond.urgency}/10</small>
        </div>
        <button type="button" class="close" id="close-cond-modal">&times;</button>
      </header>
      <p style="margin: 0 0 16px 0; color: var(--muted);">${escapeHtml(cond.description || 'No description.')}</p>

      <div class="rel-grid">
        <div class="rel-card">
          <h4>Linked Symptoms</h4>
          <div class="rel-chips">${symptomsList}</div>
        </div>
        <div class="rel-card">
          <h4>Linked Risk Factors</h4>
          <div class="rel-chips">${risksList}</div>
        </div>
        <div class="rel-card">
          <h4>Recommended Diagnostic Tests</h4>
          <div>${testsList}</div>
        </div>
        <div class="rel-card">
          <h4>Potential Treatments</h4>
          <div>${txList}</div>
        </div>
      </div>

      <div class="form-actions" style="margin-top:24px;display:flex;justify-content:space-between;align-items:center;">
        <button class="pill outline small" id="btn-open-link-rel" data-cond-id="${cond.id}" data-cond-name="${escapeHtml(cond.name)}">+ Link Symptom / Risk / Test / Treatment</button>
        <button class="pill small light" id="close-cond-modal-btn">Done</button>
      </div>
    </div>
  </div>`;

  document.body.insertAdjacentHTML('beforeend', modalHtml);
  document.querySelector('#close-cond-modal').onclick = () => document.querySelector('#condition-detail-modal').remove();
  document.querySelector('#close-cond-modal-btn').onclick = () => document.querySelector('#condition-detail-modal').remove();
  document.querySelector('#btn-open-link-rel').onclick = (e) => {
    openLinkRelationshipModal(cond.id, cond.name);
  };
}

async function openLinkRelationshipModal(conditionId, conditionName) {
  try {
    const [symptoms, risks, tests, treatments] = await Promise.all([
      api('/symptoms'),
      api('/risk-factors'),
      api('/tests'),
      api('/treatments'),
    ]);

    document.querySelector('#link-modal')?.remove();
    const modalHtml = `
    <div class="modal-backdrop" id="link-modal" style="z-index:15;">
      <form class="modal" id="link-form">
        <header>
          <div>
            <h2>Link to ${escapeHtml(conditionName)}</h2>
            <small class="muted-text">Add clinical knowledge relationship to condition</small>
          </div>
          <button type="button" class="close" id="close-link-modal">&times;</button>
        </header>

        <div class="form-stack">
          <label>Relationship Type
            <select id="rel-type-select" name="rel_type">
              <option value="symptom">Symptom</option>
              <option value="risk-factor">Risk Factor</option>
              <option value="test">Diagnostic Test</option>
              <option value="treatment">Treatment</option>
            </select>
          </label>

          <label>Select Item
            <select id="rel-item-select" name="item_id" required>
              ${symptoms.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('')}
            </select>
          </label>

          <div id="rel-dynamic-fields">
            <label>Weight (Contribution score: 0.1 to 1.0)
              <input type="number" step="0.05" min="0.1" max="1.0" name="weight" value="0.8" required>
            </label>
          </div>
        </div>

        <div class="form-actions">
          <button class="pill" type="submit">Add Relationship</button>
        </div>
      </form>
    </div>`;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    document.querySelector('#close-link-modal').onclick = () => document.querySelector('#link-modal').remove();

    const typeSelect = document.querySelector('#rel-type-select');
    const itemSelect = document.querySelector('#rel-item-select');
    const dynamicFields = document.querySelector('#rel-dynamic-fields');

    typeSelect.onchange = () => {
      const val = typeSelect.value;
      if (val === 'symptom') {
        itemSelect.innerHTML = symptoms.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
        dynamicFields.innerHTML = `<label>Weight (0.1 - 1.0)<input type="number" step="0.05" min="0.1" max="1.0" name="weight" value="0.8" required></label>`;
      } else if (val === 'risk-factor') {
        itemSelect.innerHTML = risks.map(r => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join('');
        dynamicFields.innerHTML = `<label>Weight (0.1 - 1.0)<input type="number" step="0.05" min="0.1" max="1.0" name="weight" value="0.6" required></label>`;
      } else if (val === 'test') {
        itemSelect.innerHTML = tests.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
        dynamicFields.innerHTML = `
          <label>Priority (1 = Highest, 2, 3...)<input type="number" min="1" max="10" name="priority" value="1" required></label>
          <label>Purpose for this condition<input type="text" name="purpose" placeholder="e.g. Confirm diagnosis"></label>
        `;
      } else if (val === 'treatment') {
        itemSelect.innerHTML = treatments.map(tx => `<option value="${tx.id}">${escapeHtml(tx.name)}</option>`).join('');
        dynamicFields.innerHTML = `
          <label>Priority (1 = Highest, 2, 3...)<input type="number" min="1" max="10" name="priority" value="1" required></label>
          <label>Clinical Notes<input type="text" name="notes" placeholder="e.g. Prescribe per protocol"></label>
        `;
      }
    };

    document.querySelector('#link-form').onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(e.currentTarget);
      const relType = formData.get('rel_type');
      const itemId = Number(formData.get('item_id'));

      try {
        if (relType === 'symptom') {
          await api(`/conditions/${conditionId}/symptoms`, {
            method: 'POST',
            body: JSON.stringify({ symptom_id: itemId, weight: Number(formData.get('weight')) }),
          });
        } else if (relType === 'risk-factor') {
          await api(`/conditions/${conditionId}/risk-factors`, {
            method: 'POST',
            body: JSON.stringify({ risk_factor_id: itemId, weight: Number(formData.get('weight')) }),
          });
        } else if (relType === 'test') {
          await api(`/conditions/${conditionId}/tests`, {
            method: 'POST',
            body: JSON.stringify({ test_id: itemId, priority: Number(formData.get('priority')), purpose: formData.get('purpose') || null }),
          });
        } else if (relType === 'treatment') {
          await api(`/conditions/${conditionId}/treatments`, {
            method: 'POST',
            body: JSON.stringify({ treatment_id: itemId, priority: Number(formData.get('priority')), notes: formData.get('notes') || null }),
          });
        }

        document.querySelector('#link-modal').remove();
        toast('Relationship added to condition!');
        openConditionDetails(conditionId);
      } catch (err) {
        toast(`Error: ${err.message}`);
      }
    };
  } catch (err) {
    toast(`Failed to load options for linking: ${err.message}`);
  }
}

function openResourceModal(type) {
  const config = resourceConfig[type];
  let fieldsHtml = '';

  if (type === 'conditions') {
    fieldsHtml = `
      <label>Condition Name<input name="name" placeholder="e.g. COVID-19" required></label>
      <label>Description<textarea name="description" placeholder="Clinical description..."></textarea></label>
      <div class="field-grid">
        <label>Severity (1-10)<input name="severity" type="number" min="1" max="10" value="5" required></label>
        <label>Urgency (1-10)<input name="urgency" type="number" min="1" max="10" value="5" required></label>
      </div>`;
  } else if (type === 'symptoms') {
    fieldsHtml = `
      <label>Symptom Name<input name="name" placeholder="e.g. Chills" required></label>
      <label>Description<textarea name="description" placeholder="Description of symptom..."></textarea></label>`;
  } else if (type === 'risk-factors') {
    fieldsHtml = `
      <label>Risk Factor Name<input name="name" placeholder="e.g. Obesity" required></label>
      <label>Factor Type
        <select name="factor_type">
          <option value="lifestyle">Lifestyle</option>
          <option value="demographic">Demographic</option>
          <option value="physiological">Physiological</option>
          <option value="medical_history">Medical History</option>
          <option value="environmental">Environmental</option>
        </select>
      </label>
      <label>Description<textarea name="description" placeholder="Description..."></textarea></label>`;
  } else if (type === 'tests') {
    fieldsHtml = `
      <label>Test Name<input name="name" placeholder="e.g. D-Dimer Test" required></label>
      <label>Purpose<input name="purpose" placeholder="e.g. Assess thrombosis risk"></label>
      <label>Description<textarea name="description" placeholder="Test details..."></textarea></label>`;
  } else if (type === 'treatments') {
    fieldsHtml = `
      <label>Treatment Name<input name="name" placeholder="e.g. Anticoagulant" required></label>
      <label>Treatment Type
        <select name="treatment_type">
          <option value="medication">Medication</option>
          <option value="procedure">Procedure</option>
          <option value="respiratory_support">Respiratory Support</option>
          <option value="supportive_care">Supportive Care</option>
          <option value="lifestyle">Lifestyle Intervention</option>
        </select>
      </label>
      <label>Description<textarea name="description" placeholder="Treatment details..."></textarea></label>`;
  }

  document.querySelector('#resource-modal')?.remove();
  document.body.insertAdjacentHTML(
    'beforeend',
    `
    <div class="modal-backdrop" id="resource-modal">
      <form class="modal" id="resource-form">
        <header>
          <h2>Add ${config.singular}</h2>
          <button type="button" class="close" id="close-modal">&times;</button>
        </header>
        <div class="form-stack">
          ${fieldsHtml}
        </div>
        <div class="form-actions">
          <button class="pill" type="submit">Create ${config.singular}</button>
        </div>
      </form>
    </div>`
  );

  document.querySelector('#close-modal').onclick = () => document.querySelector('#resource-modal').remove();
  document.querySelector('#resource-form').onsubmit = async event => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    if (payload.severity) payload.severity = Number(payload.severity);
    if (payload.urgency) payload.urgency = Number(payload.urgency);

    try {
      await api(`/${type}`, { method: 'POST', body: JSON.stringify(payload) });
      document.querySelector('#resource-modal').remove();
      delete state.data[type];
      await loadResource(type);
      loadStats();
      toast(`${config.label.slice(0, -1)} added to database!`);
    } catch (error) {
      toast(`Error: ${error.message}`);
    }
  };
}

function toast(message) {
  document.querySelectorAll('.toast').forEach(t => t.remove());
  document.body.insertAdjacentHTML('beforeend', `<div class="toast">${escapeHtml(message)}</div>`);
  setTimeout(() => document.querySelector('.toast')?.remove(), 3400);
}

function bindEvents() {
  document.querySelectorAll('[data-page]').forEach(element => {
    element.onclick = event => {
      event.preventDefault();
      const page = element.dataset.page;
      if (page === 'home') {
        state.page = 'home';
        render();
      } else {
        go(page);
      }
    };
  });

  const menu = document.querySelector('#menu-button');
  if (menu) {
    menu.onclick = () => document.querySelector('#sidebar').classList.toggle('open');
  }

  document.querySelector('#btn-seed-data')?.addEventListener('click', () => {
    triggerSeed();
  });

  document.querySelector('#evaluation-form')?.addEventListener('submit', event => {
    event.preventDefault();
    submitEvaluation(event.currentTarget);
  });

  document.querySelector('#btn-save-record')?.addEventListener('click', () => {
    saveCurrentEvaluation();
  });

  document.querySelectorAll('.btn-view-rec').forEach(el => {
    el.onclick = () => {
      const recId = Number(el.dataset.recId);
      const rec = state.evaluations.find(r => r.id === recId);
      if (rec && rec.results_json) {
        try {
          state.results = JSON.parse(rec.results_json);
          state.savedRecordId = rec.id;
          state.page = 'results';
          render();
        } catch (e) {
          toast('Failed to load assessment report.');
        }
      }
    };
  });

  document.querySelectorAll('.btn-cond-detail').forEach(el => {
    el.onclick = () => {
      const condId = Number(el.dataset.condId);
      openConditionDetails(condId);
    };
  });

  document.querySelectorAll('[data-add]').forEach(element => {
    element.onclick = () => {
      const key = element.dataset.add === 'symptoms' ? 'selectedSymptoms' : 'selectedRisks';
      if (!state[key].includes(element.dataset.value)) {
        state[key].push(element.dataset.value);
      }
      render();
    };
  });

  document.querySelectorAll('[data-remove]').forEach(element => {
    element.onclick = () => {
      const key = element.dataset.remove === 'symptoms' ? 'selectedSymptoms' : 'selectedRisks';
      state[key] = state[key].filter(value => value !== element.dataset.value);
      render();
    };
  });

  document.querySelectorAll('[data-search]').forEach(element => {
    element.oninput = event => {
      const key = event.target.dataset.search === 'symptoms' ? 'symptomsQuery' : 'risksQuery';
      state[key] = event.target.value;
      render();
      document.querySelector(`[data-search="${event.target.dataset.search}"]`)?.focus();
    };
  });

  document.querySelectorAll('[data-expand]').forEach(element => {
    element.onclick = () => {
      state.expanded = Number(element.dataset.expand) === state.expanded ? -1 : Number(element.dataset.expand);
      render();
    };
  });

  document.querySelector('#kb-search')?.addEventListener('input', event => {
    state.kbQuery = event.target.value;
    render();
    document.querySelector('#kb-search')?.focus();
  });

  document.querySelector('[data-add-resource]')?.addEventListener('click', event => {
    openResourceModal(event.currentTarget.dataset.addResource);
  });
}

// Initial render
render();
if (state.page === 'home' || state.page === 'overview') {
  loadStats();
}
