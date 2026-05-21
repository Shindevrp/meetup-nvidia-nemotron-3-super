const API_BASE = window.location.origin;

// State
let chatHistory = [];
let currentLang = 'english';
let allSchemes = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initLang();
  loadSchemes();
});

function initLang() {
  const saved = localStorage.getItem('lang');
  if (saved === 'hindi') {
    currentLang = 'hindi';
    document.getElementById('lang-toggle').textContent = 'English';
  }
}

function toggleLang() {
  currentLang = currentLang === 'english' ? 'hindi' : 'english';
  localStorage.setItem('lang', currentLang);
  document.getElementById('lang-toggle').textContent = currentLang === 'english' ? 'हिन्दी' : 'English';

  if (currentLang === 'hindi') {
    document.getElementById('subtitle').textContent = 'भारत सरकार की कल्याणकारी योजनाओं के लिए सहायक';
    document.getElementById('eligibility-desc').textContent = 'अपनी पात्रता जांचने के लिए नीचे दिए गए प्रश्नों के उत्तर दें।';
  } else {
    document.getElementById('subtitle').textContent = 'Indian Government Welfare Schemes Assistant';
    document.getElementById('eligibility-desc').textContent = 'Answer a few questions to find which schemes you may qualify for.';
  }
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

  document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
}

// CHAT
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  addMessage(msg, 'user');
  input.value = '';
  input.style.height = 'auto';

  showTyping();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        language: currentLang,
        history: chatHistory.slice(-6),
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    removeTyping();
    addMessage(data.reply, 'bot', data.citations, data.confidence);

    chatHistory.push({ role: 'user', content: msg });
    chatHistory.push({ role: 'assistant', content: data.reply });

    showConfidence(data.confidence);
  } catch (err) {
    removeTyping();
    addMessage('Sorry, I encountered an error. Please check that the backend server is running and try again.', 'bot');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function addMessage(text, role, citations, confidence) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;

  let html = `<div class="bubble">${formatText(text)}`;

  if (citations && citations.length > 0) {
    html += '<div class="citations">';
    citations.forEach(c => {
      const cls = c.confidence > 0.6 ? 'conf-high' : c.confidence > 0.3 ? 'conf-med' : 'conf-low';
      html += `<div class="citation"><span class="conf-badge ${cls}">${(c.confidence * 100).toFixed(0)}%</span> ${c.scheme} — ${c.section}</div>`;
    });
    html += '</div>';
  }

  if (role === 'bot') {
    html += '<div class="disclaimer">⚠️ AI-generated — verify with official sources</div>';
  }

  html += '</div>';
  div.innerHTML = html;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function formatText(text) {
  return text
    .replace(/\n/g, '<br/>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.*)/gm, '• $1');
}

function showTyping() {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = 'typing-indicator';
  div.innerHTML = '<div class="bubble typing"><span></span><span></span><span></span></div>';
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function showConfidence(confidence) {
  const indicator = document.getElementById('confidence-indicator');
  const dot = document.getElementById('conf-dot');
  const label = document.getElementById('conf-label');

  indicator.classList.remove('hidden');
  dot.className = 'dot';

  if (confidence > 0.6) {
    dot.classList.add('high');
    label.textContent = `High confidence (${(confidence * 100).toFixed(0)}%)`;
  } else if (confidence > 0.3) {
    dot.classList.add('med');
    label.textContent = `Medium confidence (${(confidence * 100).toFixed(0)}%) — verify with official sources`;
  } else {
    dot.classList.add('low');
    label.textContent = `Low confidence (${(confidence * 100).toFixed(0)}%) — please verify thoroughly`;
  }
}

// ELIGIBILITY
async function checkEligibility(event) {
  event.preventDefault();

  const profile = {
    age: parseInt(document.getElementById('el-age').value) || null,
    annual_income: parseFloat(document.getElementById('el-income').value) || null,
    occupation: document.getElementById('el-occupation').value || null,
    gender: document.getElementById('el-gender').value || null,
    landowner: document.getElementById('el-landowner').checked,
    is_student: document.getElementById('el-student').checked,
    has_lpg: document.getElementById('el-has-lpg').checked,
    owns_pucca_house: document.getElementById('el-owns-house').checked,
  };

  const resultsDiv = document.getElementById('eligibility-results');
  resultsDiv.classList.remove('hidden');
  resultsDiv.innerHTML = '<p>Checking eligibility...</p>';

  try {
    const res = await fetch(`${API_BASE}/api/eligibility`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    const data = await res.json();

    let html = '<h3>Results</h3>';
    data.forEach(s => {
      const isMatch = s.match;
      html += `
        <div class="result-card">
          <h3>${s.name}</h3>
          <div class="match-badge match-${isMatch}">${isMatch ? '✅ Likely Eligible' : '⚠️ May Not Qualify'}</div>
          <div class="confidence-bar"><div class="confidence-fill" style="width:${s.confidence * 100}%"></div></div>
          <div style="font-size:0.85rem;color:var(--text-secondary)">Match confidence: ${(s.confidence * 100).toFixed(0)}%</div>
          ${s.reasons.length ? `<div class="reasons">⚠️ ${s.reasons.join('; ')}</div>` : ''}
        </div>
      `;
    });

    html += '<div class="disclaimer" style="margin-top:12px">⚠️ This is an estimate based on limited information. Visit official portals for confirmation.</div>';
    resultsDiv.innerHTML = html;
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    resultsDiv.innerHTML = '<p style="color:var(--danger)">Error checking eligibility. Is the backend running?</p>';
  }
}

// SCHEMES
async function loadSchemes() {
  try {
    const res = await fetch(`${API_BASE}/api/schemes`);
    allSchemes = await res.json();
    renderSchemeList(Object.keys(allSchemes));
  } catch (err) {
    document.getElementById('scheme-list').innerHTML = '<p style="color:var(--danger)">Could not load schemes. Is the backend running?</p>';
  }
}

function renderSchemeList(ids) {
  const list = document.getElementById('scheme-list');
  let html = '';
  ids.forEach(id => {
    const s = allSchemes[id];
    html += `
      <div class="scheme-card" onclick="showSchemeDetail('${id}')">
        <h3>${currentLang === 'hindi' && s.name_hi ? s.name_hi : s.name}</h3>
        <p>${s.summary}</p>
        <span class="scheme-tag">${id}</span>
      </div>
    `;
  });
  list.innerHTML = html || '<p>No schemes match your search.</p>';
}

function filterSchemes() {
  const q = document.getElementById('scheme-search').value.toLowerCase();
  const ids = Object.keys(allSchemes).filter(id => {
    const s = allSchemes[id];
    return id.includes(q) || s.name.toLowerCase().includes(q) || s.summary.toLowerCase().includes(q);
  });
  renderSchemeList(ids);
}

async function showSchemeDetail(id) {
  document.getElementById('scheme-list').classList.add('hidden');
  const detail = document.getElementById('scheme-detail');
  detail.classList.remove('hidden');

  try {
    const res = await fetch(`${API_BASE}/api/schemes/${id}`);
    const s = await res.json();

    const name = currentLang === 'hindi' && s.name_hi ? `${s.name} (${s.name_hi})` : s.name;

    let faqHtml = '';
    if (s.faq && s.faq.length) {
      faqHtml = '<section><h4>❓ Common Questions</h4>';
      s.faq.forEach(f => {
        faqHtml += `<div class="faq-item"><strong>${f.q}</strong><p>${f.a}</p></div>`;
      });
      faqHtml += '</section>';
    }

    detail.innerHTML = `
      <a class="back-link" onclick="backToSchemeList()">← Back to all schemes</a>
      <h3>${name}</h3>
      <div class="meta">${s.ministry} | ${s.type}</div>
      <p>${s.summary}</p>

      <section>
        <h4>✅ Benefits</h4>
        <ul>${s.benefits.map(b => `<li>${b}</li>`).join('')}</ul>
      </section>

      ${s.eligibility ? `
      <section>
        <h4>👤 Who Can Apply</h4>
        <ul>${(s.eligibility.who_can_apply || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </section>
      <section>
        <h4>❌ Who Cannot Apply</h4>
        <ul>${(s.eligibility.who_cannot_apply || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </section>
      <section>
        <h4>📄 Documents Required</h4>
        <ul>${(s.eligibility.documents_required || []).map(x => `<li>${x}</li>`).join('')}</ul>
      </section>` : ''}

      ${s.application_process ? `
      <section>
        <h4>📝 How to Apply</h4>
        ${typeof s.application_process.how_to_apply === 'string'
          ? `<p>${s.application_process.how_to_apply}</p>`
          : `<ul>${s.application_process.how_to_apply.map(x => `<li>${x}</li>`).join('')}</ul>`
        }
        ${s.application_process.portal_url ? `<p>🔗 <a href="${s.application_process.portal_url}" target="_blank">${s.application_process.portal_url}</a></p>` : ''}
        ${s.application_process.helpline ? `<p>📞 Helpline: ${s.application_process.helpline}</p>` : ''}
      </section>` : ''}

      ${faqHtml}

      <section>
        <h4>📚 Official Sources</h4>
        <ul>${s.official_sources.map(src => `<li><a href="${src}" target="_blank">${src}</a></li>`).join('')}</ul>
      </section>
    `;
  } catch (err) {
    detail.innerHTML = '<p style="color:var(--danger)">Error loading scheme details.</p>';
  }
}

function backToSchemeList() {
  document.getElementById('scheme-list').classList.remove('hidden');
  document.getElementById('scheme-detail').classList.add('hidden');
}
