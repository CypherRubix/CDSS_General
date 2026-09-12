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
  results: null,
  error: '',
  loading: false,
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
          <span>clarity<span class="brand-dot">.</span></span>
        </a>
        <span class="title-tag">Clinical Decision Support</span>
      </div>

      <nav class="top-nav" aria-label="Main navigation">
        <a href="#" data-page="home">Home</a>
        <a href="#" data-page="overview">Workspace</a>
        <a href="#" data-page="knowledge">Knowledge Base</a>
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

  const content = state.page === 'home'
    ? landingPage()
    : state.page === 'overview'
      ? overviewPage()
      : state.page === 'evaluate'
        ? evaluationPage()
        : state.page === 'results'
          ? resultsPage()
          : state.page === 'knowledge'
            ? knowledgePage('conditions')
            : state.page.startsWith('knowledge:')
              ? knowledgePage(state.page.split(':')[1] || 'conditions')
              : overviewPage();

  app.innerHTML = `${titleBar()}<main class="main-shell">${content}</main>`;
  bindEvents();
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

  return `
    ${pageHead('Evaluation', 'Patient evaluation', 'Select observed symptoms and relevant risk factors to generate a decision-support assessment.')}
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
            <h3>Symptoms</h3>
            ${selector('symptoms', state.selectedSymptoms, symptoms, 'Search symptoms...')}
          </div>

          <div class="form-section">
            <h3>Risk factors</h3>
            ${selector('risk-factors', state.selectedRisks, risks, 'Search risk factors...')}
          </div>

          <div class="form-actions">
            <button class="pill" type="submit">${state.loading ? 'Evaluating...' : 'Evaluate Patient'}</button>
          </div>
        </form>
      </section>

      <aside class="panel">
        <h2>Knowledge base status</h2>
        <div class="info-list" style="margin-top:22px;">
          <div class="info-item"><span>Symptoms available</span><strong>${symptoms.length}</strong></div>
          <div class="info-item"><span>Risk factors available</span><strong>${risks.length}</strong></div>
        </div>
      </aside>
    </div>
  `;
}

function selector(type, selected, values, placeholder) {
  const queryKey = type === 'symptoms' ? 'symptomsQuery' : 'risksQuery';
  const query = state[queryKey] || '';
  const filtered = values.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()) && !selected.includes(item.name)).slice(0, 8);

  return `
    <div class="choice-box">
      ${selected.map((item) => `
        <span class="choice">${escapeHtml(item)}
          <button type="button" data-remove="${type}" data-value="${escapeHtml(item)}">&times;</button>
        </span>
      `).join('')}
      <input data-search="${type}" value="${escapeHtml(query)}" placeholder="${escapeHtml(placeholder)}">
    </div>
    <div class="suggestions">
      ${filtered.map((item) => `<button type="button" class="suggestion" data-add="${type}" data-value="${escapeHtml(item.name)}">+ ${escapeHtml(item.name)}</button>`).join('')}
    </div>
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
  return `
    ${pageHead('Results', 'Evaluation assessment', 'Candidate conditions ranked by stored relationships and severity.', '<button class="pill" data-page="evaluate">New evaluation</button>')}
    <div class="results-list">
      ${rows.length ? rows.map((item, index) => resultCard(item, index)).join('') : '<div class="panel empty">No ranked conditions matched the submitted symptoms.</div>'}
    </div>
  `;
}

function resultCard(item, index) {
  const percentage = Math.round((item.likelihood_score || 0) * 100);
  const detail = `
    <div class="condition-detail">
      <div>
        <h4>Matched symptoms</h4>
        <ul class="detail-list">${(item.matched_symptoms || []).map((s) => `<li>${escapeHtml(s.name)} (${s.weight})</li>`).join('') || '<li>None matched</li>'}</ul>
      </div>
      <div>
        <h4>Matched risk factors</h4>
        <ul class="detail-list">${(item.matched_risk_factors || []).map((s) => `<li>${escapeHtml(s.name)} (${s.weight})</li>`).join('') || '<li>None matched</li>'}</ul>
      </div>
      <div>
        <h4>Recommended tests</h4>
        <ul class="detail-list">${(item.recommended_tests || []).map((test) => `<li>${escapeHtml(test.name)}</li>`).join('') || '<li>None stored</li>'}</ul>
      </div>
      <div>
        <h4>Potential treatments</h4>
        <ul class="detail-list">${(item.treatments || []).map((tx) => `<li>${escapeHtml(tx.name)}</li>`).join('') || '<li>None stored</li>'}</ul>
      </div>
    </div>
  `;

  return `
    <article class="condition-card">
      <div class="condition-summary" data-expand="${index}">
        <div>
          <h3>${escapeHtml(item.condition)}</h3>
          <small>Priority score: ${item.priority_score}</small>
        </div>
        <div class="metric"><span>Likelihood</span><strong>${percentage}%</strong></div>
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

      ${state.loading ? '<div class="loading">Loading records...</div>' : filtered.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>${type === 'conditions' ? 'Severity / Urgency' : type === 'risk-factors' ? 'Factor Type' : type === 'tests' ? 'Purpose' : 'Info'}</th>
              </tr>
            </thead>
            <tbody>
              ${filtered.map((item) => `
                <tr>
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
      ` : '<div class="empty">No records found in this category.</div>'}
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

  document.querySelectorAll('[data-add]').forEach((el) => {
    el.onclick = () => {
      const type = el.dataset.add;
      const key = type === 'symptoms' ? 'selectedSymptoms' : 'selectedRisks';
      const value = el.dataset.value;
      if (!state[key].includes(value)) {
        state[key].push(value);
      }
      render();
    };
  });

  document.querySelectorAll('[data-remove]').forEach((el) => {
    el.onclick = () => {
      const type = el.dataset.remove;
      const key = type === 'symptoms' ? 'selectedSymptoms' : 'selectedRisks';
      const value = el.dataset.value;
      state[key] = state[key].filter((item) => item !== value);
      render();
    };
  });

  document.querySelectorAll('[data-search]').forEach((el) => {
    el.oninput = (event) => {
      const key = event.target.dataset.search === 'symptoms' ? 'symptomsQuery' : 'risksQuery';
      state[key] = event.target.value;
      render();
    };
  });

  document.querySelector('#kb-search')?.addEventListener('input', (event) => {
    state.kbQuery = event.target.value;
    render();
  });
}

async function init() {
  try {
    state.data.symptoms = await api('/symptoms');
    state.data['risk-factors'] = await api('/risk-factors');
    state.stats = await api('/stats');
  } catch (error) {
    state.error = error.message;
  }
  render();
}

init();

