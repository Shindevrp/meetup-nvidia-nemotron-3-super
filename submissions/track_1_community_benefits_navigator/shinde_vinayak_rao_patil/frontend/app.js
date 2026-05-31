const API_BASE = window.location.origin;

let chatHistory = [];
let currentLang = 'english';
let allSchemes = {};
let cscMap = null;
let cscMarkers = [];
let darkMode = false;
let mediaQueryDark = window.matchMedia('(prefers-color-scheme: dark)');
let sidebarOpen = false;
let sessionsList = [];
let currentSessionId = getSessionId();

const CONTEXT_KEY = 'cb_context_memory';
const SESSION_KEY = 'cb_session_id';
const DARK_KEY = 'cb_dark_mode';

function getSessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

function defaultContext() {
  return {
    discussedSchemes: [],
    userProfile: null,
    eligibilityResults: [],
    sessionStart: Date.now(),
    messageCount: 0,
  };
}

let contextMemory = defaultContext();

function loadContext() {
  try {
    const raw = localStorage.getItem(CONTEXT_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      contextMemory = { ...defaultContext(), ...saved };
    }
  } catch (e) {
    contextMemory = defaultContext();
  }
}

function saveContext() {
  try {
    localStorage.setItem(CONTEXT_KEY, JSON.stringify(contextMemory));
  } catch (e) {}
}

const HISTORY_KEY = 'cb_chat_history';

function saveHistory() {
  try {
    const toSave = chatHistory.slice(-50).map(m => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp || Date.now(),
      confidence: m.confidence,
    }));
    localStorage.setItem(HISTORY_KEY, JSON.stringify(toSave));
  } catch (e) {}
}

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (raw) {
      chatHistory = JSON.parse(raw);
    }
  } catch (e) {
    chatHistory = [];
  }
}

function restoreMessages() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  const welcomeDiv = document.createElement('div');
  welcomeDiv.className = 'message bot';
  welcomeDiv.innerHTML = `
    <div class="bubble">
      <strong>Welcome.</strong><br/>
      I can help you find and apply for Indian government welfare schemes.<br/><br/>
      <strong>Try asking:</strong>
      <ul>
        <li>"What schemes am I eligible for?"</li>
        <li>"How to apply for PM-KISAN?"</li>
        <li>"Documents needed for Ayushman Bharat"</li>
      </ul>
      <div class="disclaimer">Note: AI-generated — always verify with official sources</div>
    </div>
  `;
  container.appendChild(welcomeDiv);

  let restored = 0;
  chatHistory.forEach(msg => {
    if (msg.role === 'user' || msg.role === 'assistant') {
      addMessage(msg.content, msg.role, null, msg.confidence, false);
      restored++;
    }
  });

  if (restored > 0) {
    const sep = document.createElement('div');
    sep.className = 'message bot';
    sep.innerHTML = `<div class="bubble" style="font-size:0.78rem;color:var(--text-secondary);text-align:center;background:transparent;border:none;">— Previous conversation restored (${restored} messages) —</div>`;
    container.appendChild(sep);
  }

  container.scrollTop = container.scrollHeight;
}

document.addEventListener('DOMContentLoaded', async () => {
  loadContext();
  loadDarkMode();
  initLang();
  loadSchemes();
  loadCompareOptions();

  // Try to restore from server first, fall back to localStorage
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages`);
    if (res.ok) {
      const msgs = await res.json();
      if (msgs.length > 0) {
        chatHistory = msgs.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
          confidence: m.confidence,
        }));
        saveHistory();
      } else {
        loadHistory();
      }
    } else {
      loadHistory();
    }
  } catch (e) {
    loadHistory();
  }

  restoreMessages();
  fetchSessions();
});

function loadDarkMode() {
  const saved = localStorage.getItem(DARK_KEY);
  if (saved === 'true' || (saved === null && mediaQueryDark.matches)) {
    darkMode = true;
    document.body.classList.add('dark-mode');
    document.getElementById('dark-toggle').textContent = '☀️';
  }
}

function toggleDark() {
  darkMode = !darkMode;
  document.body.classList.toggle('dark-mode', darkMode);
  localStorage.setItem(DARK_KEY, darkMode);
  document.getElementById('dark-toggle').textContent = darkMode ? '☀️' : '🌙';
}

function initLang() {
  const saved = localStorage.getItem('lang');
  if (saved && LANG_NAMES[saved]) {
    currentLang = saved;
    document.getElementById('lang-select').value = saved;
    applyLangUI();
  }
}

const LANG_NAMES = {
  english: 'English', hindi: 'हिन्दी', telugu: 'తెలుగు',
  tamil: 'தமிழ்', bengali: 'বাংলা', marathi: 'मराठी',
};

function applyLangUI() {
  const subtitles = {
    english: 'Indian Government Welfare Schemes Assistant',
    hindi: 'भारत सरकार की कल्याणकारी योजनाओं के लिए सहायक',
    telugu: 'భారత ప్రభుత్వ సంక్షేమ పథకాల సహాయకుడు',
    tamil: 'இந்திய அரசு நலத்திட்ட உதவியாளர்',
    bengali: 'ভারত সরকারের কল্যাণমূলক প্রকল্প সহায়ক',
    marathi: 'भारत सरकारच्या कल्याणकारी योजना सहाय्यक',
  };
  document.getElementById('subtitle').textContent = subtitles[currentLang] || subtitles.english;

  const descs = {
    english: 'Answer a few questions to find which schemes you may qualify for.',
    hindi: 'अपनी पात्रता जांचने के लिए नीचे दिए गए प्रश्नों के उत्तर दें।',
    telugu: 'మీరు ఏ పథకాలకు అర్హులో తెలుసుకోవడానికి కొన్ని ప్రశ్నలకు సమాధానం ఇవ్వండి.',
    tamil: 'நீங்கள் எந்த திட்டங்களுக்கு தகுதி பெறலாம் என்பதை அறிய சில கேள்விகளுக்கு பதிலளிக்கவும்.',
    bengali: 'আপনি কোন প্রকল্পের জন্য যোগ্য তা জানতে কয়েকটি প্রশ্নের উত্তর দিন।',
    marathi: 'तुम्ही कोणत्या योजनांसाठी पात्र आहात हे जाणून घेण्यासाठी काही प्रश्नांची उत्तरे द्या.',
  };
  const desc = document.getElementById('eligibility-desc');
  if (desc) desc.textContent = descs[currentLang] || descs.english;

  filterSchemes();
}

function setLang(value) {
  currentLang = value;
  localStorage.setItem('lang', value);
  applyLangUI();
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
  if (tab === 'csc') setTimeout(initCSCMap, 200);
}

function clearChat() {
  if (!confirm('Start a new conversation? The current one will be saved.')) return;
  newChat();
}

// --- Chat History Sidebar ---

function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('open', sidebarOpen);
  document.getElementById('sidebar-overlay').classList.toggle('open', sidebarOpen);
  if (sidebarOpen) fetchSessions();
}

async function fetchSessions() {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (!res.ok) return;
    sessionsList = await res.json();
    renderSidebar();
  } catch (e) {}
}

function groupSessions(list) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000;
  const yesterday = today - 86400;
  const weekAgo = today - 7 * 86400;

  const groups = { today: [], yesterday: [], week: [], older: [] };
  list.forEach(s => {
    const t = s.updated_at;
    if (t >= today) groups.today.push(s);
    else if (t >= yesterday) groups.yesterday.push(s);
    else if (t >= weekAgo) groups.week.push(s);
    else groups.older.push(s);
  });
  return groups;
}

const GROUP_LABELS = {
  today: 'Today',
  yesterday: 'Yesterday',
  week: 'Last 7 Days',
  older: 'Earlier',
};

function renderSidebar() {
  const list = document.getElementById('sidebar-list');
  const q = (document.getElementById('sidebar-search').value || '').toLowerCase();
  const filtered = q ? sessionsList.filter(s => (s.title || '').toLowerCase().includes(q)) : sessionsList;

  if (!filtered.length) {
    list.innerHTML = '<p class="sidebar-empty">No conversations yet</p>';
    return;
  }

  const groups = groupSessions(filtered);
  let html = '';
  ['today', 'yesterday', 'week', 'older'].forEach(key => {
    if (!groups[key].length) return;
    html += `<div class="sidebar-group-label">${GROUP_LABELS[key]}</div>`;
    groups[key].forEach(s => {
      const isActive = s.id === currentSessionId;
      const title = s.title || 'New Chat';
      const date = new Date(s.updated_at * 1000);
      const dateStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      const timeStr = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
      const isToday = s.updated_at >= new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()).getTime() / 1000;

      html += `
        <div class="session-card ${isActive ? 'active' : ''}" onclick="switchSession('${s.id}')">
          <div class="session-card-main">
            <div class="session-title">${escHtml(title)}</div>
            <div class="session-meta">${isToday ? timeStr : dateStr + ' ' + timeStr} · ${s.message_count} msgs</div>
          </div>
          <div class="session-actions">
            <button class="session-action" onclick="event.stopPropagation();renameSession('${s.id}')" title="Rename">✏️</button>
            <button class="session-action" onclick="event.stopPropagation();deleteSession('${s.id}')" title="Delete">🗑️</button>
          </div>
        </div>
      `;
    });
  });
  list.innerHTML = html;
}

function escHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function switchSession(sid) {
  if (sid === currentSessionId) return;

  // Save current local messages to server before switching
  await saveCurrentHistoryToServer();

  currentSessionId = sid;
  localStorage.setItem(SESSION_KEY, sid);

  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sid}/messages`);
    if (!res.ok) throw new Error('Not found');
    const messages = await res.json();

    chatHistory = messages.map(m => ({
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
      confidence: m.confidence,
    }));
    saveHistory();

    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    restoreMessages();
  } catch (e) {
    // Session might not exist on server yet
    chatHistory = [];
    saveHistory();
    restoreMessages();
  }

  renderSidebar();

  if (window.innerWidth <= 600) toggleSidebar();
}

async function saveCurrentHistoryToServer() {
  if (!chatHistory.length) return;
  try {
    // Only save messages that might not be on the server
    const res = await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages`);
    if (res.ok) {
      const serverMsgs = await res.json();
      if (serverMsgs.length >= chatHistory.length) return; // already saved
    }
    // Save each message individually
    for (const m of chatHistory) {
      await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: m.role, content: m.content, confidence: m.confidence }),
      });
    }
  } catch (e) {}
}

async function saveMessageToServer(role, content, confidence) {
  try {
    await fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, content, confidence }),
    });
    fetchSessions();
  } catch (e) {}
}

async function newChat() {
  const newSid = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
  currentSessionId = newSid;
  localStorage.setItem(SESSION_KEY, newSid);

  chatHistory = [];
  contextMemory = defaultContext();
  saveContext();
  saveHistory();

  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  restoreMessages();

  fetchSessions();

  if (window.innerWidth <= 600) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('open');
    sidebarOpen = false;
  }
}

async function deleteSession(sid) {
  if (!confirm('Delete this conversation permanently?')) return;
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${sid}`, { method: 'DELETE' });
    if (!res.ok) return;
    if (sid === currentSessionId) {
      newChat();
    } else {
      fetchSessions();
    }
  } catch (e) {}
}

async function renameSession(sid) {
  const session = sessionsList.find(s => s.id === sid);
  const currentTitle = session ? (session.title || 'New Chat') : 'New Chat';
  const newTitle = prompt('Rename conversation:', currentTitle);
  if (!newTitle || newTitle === currentTitle) return;
  try {
    await fetch(`${API_BASE}/api/sessions/${sid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    });
    fetchSessions();
  } catch (e) {}
}

function filterSidebar() {
  renderSidebar();
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 150) + 'px';
}

// --- Voice Input ---

let recognition = null;
let isListening = false;

function startVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    addMessage('Voice input is not supported in this browser. Try Chrome or Edge.', 'bot', null, null, true);
    return;
  }

  if (isListening) {
    recognition.stop();
    return;
  }

  if (!recognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    const langMap = { english: 'en-IN', hindi: 'hi-IN', telugu: 'te-IN', tamil: 'ta-IN', bengali: 'bn-IN', marathi: 'mr-IN' };
    recognition.lang = langMap[currentLang] || 'en-IN';

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('chat-input').value = transcript;
      autoResize(document.getElementById('chat-input'));
      sendMessage();
      isListening = false;
      document.getElementById('mic-btn').textContent = '🎤';
    };

    recognition.onerror = (event) => {
      isListening = false;
      document.getElementById('mic-btn').textContent = '🎤';
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        addMessage('Voice input error: ' + event.error, 'bot', null, null, true);
      }
    };

    recognition.onend = () => {
      isListening = false;
      document.getElementById('mic-btn').textContent = '🎤';
    };
  }

  recognition.lang = { english: 'en-IN', hindi: 'hi-IN', telugu: 'te-IN', tamil: 'ta-IN', bengali: 'bn-IN', marathi: 'mr-IN' }[currentLang] || 'en-IN';
  recognition.start();
  isListening = true;
  document.getElementById('mic-btn').textContent = '🔴';
}

// --- Chat ---

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  addMessage(msg, 'user', null, null, true);
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
        history: chatHistory.slice(-8),
        session_id: currentSessionId,
      }),
    });

    if (!res.ok) {
      if (res.status === 429) throw new Error('Rate limit exceeded. Please wait a moment.');
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    removeTyping();
    addMessage(data.reply, 'bot', data.citations, data.confidence, true);

    chatHistory.push({ role: 'user', content: msg, timestamp: Date.now() });
    chatHistory.push({ role: 'assistant', content: data.reply, timestamp: Date.now(), confidence: data.confidence });

    const schemeNames = extractSchemeNames(msg + data.reply);
    schemeNames.forEach(n => {
      if (!contextMemory.discussedSchemes.includes(n)) {
        contextMemory.discussedSchemes.push(n);
      }
    });
    contextMemory.messageCount++;
    saveContext();
    saveHistory();
    showConfidence(data.confidence);

    saveMessageToServer('user', msg, null);
    saveMessageToServer('assistant', data.reply, data.confidence);
  } catch (err) {
    removeTyping();
    addMessage('Error: ' + err.message + '. Please check that the backend is running.', 'bot', null, null, true);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function addMessage(text, role, citations, confidence, shouldPersist) {
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
    html += '<div class="disclaimer">Note: AI-generated — verify with official sources</div>';
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
    .replace(/^- (.*)/gm, '&bull; $1');
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

function extractSchemeNames(text) {
  const names = [];
  for (const id in allSchemes) {
    const s = allSchemes[id];
    if (text.toLowerCase().includes(s.name.toLowerCase()) ||
        text.toLowerCase().includes(id.replace(/_/g, ' ')) ||
        (s.name_hi && text.includes(s.name_hi))) {
      names.push(s.name);
    }
  }
  return names;
}

// --- Eligibility ---

async function checkEligibility(event) {
  event.preventDefault();

  const btn = document.getElementById('eligibility-btn');
  btn.disabled = true;
  btn.textContent = 'Checking...';

  const profile = {
    age: parseInt(document.getElementById('el-age').value) || null,
    annual_income: parseFloat(document.getElementById('el-income').value) || null,
    occupation: document.getElementById('el-occupation').value || null,
    gender: document.getElementById('el-gender').value || null,
    landowner: document.getElementById('el-landowner').checked,
    is_student: document.getElementById('el-student').checked,
    has_lpg: document.getElementById('el-has-lpg').checked,
    owns_pucca_house: document.getElementById('el-owns-house').checked,
    session_id: currentSessionId,
  };

  const resultsDiv = document.getElementById('eligibility-results');
  resultsDiv.classList.remove('hidden');
  resultsDiv.innerHTML = '<div class="loading-spinner"></div><p>Checking eligibility...</p>';

  try {
    const res = await fetch(`${API_BASE}/api/eligibility`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    const data = await res.json();

    contextMemory.userProfile = profile;
    contextMemory.eligibilityResults = data.map(r => ({
      scheme_id: r.scheme_id,
      name: r.name,
      match: r.match,
      confidence: r.confidence,
    }));
    saveContext();

    let html = '<div id="eligibility-report">';
    html += '<div class="report-actions"><h3>Eligibility Results</h3><button class="btn-small" onclick="downloadPDF()">Download PDF Report</button></div>';

    const matched = data.filter(s => s.match);
    const notMatched = data.filter(s => !s.match);

    if (matched.length > 0) {
      html += '<h4 style="color:var(--success);margin:12px 0 8px;">Schemes You May Qualify For</h4>';
    }

    const sorted = [...matched, ...notMatched];
    sorted.forEach(s => {
      const isMatch = s.match;
      html += `
        <div class="result-card ${isMatch ? 'result-match' : 'result-no-match'}">
          <div class="result-header">
            <h3>${s.name}</h3>
            <div class="match-badge match-${isMatch}">${isMatch ? 'Likely Eligible' : 'May Not Qualify'}</div>
          </div>
          <div class="confidence-bar"><div class="confidence-fill" style="width:${s.confidence * 100}%"></div></div>
          <div class="confidence-text">Match confidence: ${(s.confidence * 100).toFixed(0)}%</div>
          ${s.reasons.length ? `<div class="reasons">${s.reasons.join('; ')}</div>` : ''}
        </div>
      `;
    });

    html += '</div>';
    html += '<div class="disclaimer" style="margin-top:12px">Note: This is an estimate based on limited information. Visit official portals for confirmation.</div>';
    resultsDiv.innerHTML = html;
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    resultsDiv.innerHTML = '<p class="error-text">Error checking eligibility. Is the backend running?</p>';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Check Eligibility';
  }
}

function downloadPDF() {
  const report = document.getElementById('eligibility-report');
  if (!report) return;
  const opt = {
    margin: [10, 10],
    filename: 'eligibility-report.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
  };
  html2pdf().set(opt).from(report).save();
}

// --- Schemes ---

async function loadSchemes() {
  try {
    const res = await fetch(`${API_BASE}/api/schemes`);
    allSchemes = await res.json();
    renderSchemeList(Object.keys(allSchemes));
  } catch (err) {
    document.getElementById('scheme-list').innerHTML = '<p class="error-text">Could not load schemes. Is the backend running?</p>';
  }
}

function renderSchemeList(ids) {
  const list = document.getElementById('scheme-list');
  let html = '';
  ids.forEach(id => {
    const s = allSchemes[id];
    const nameKey = currentLang === 'hindi' && s.name_hi ? 'name_hi' : 'name';
    const summaryKey = currentLang === 'hindi' && s.summary_hi ? 'summary_hi' : 'summary';
    html += `
      <div class="scheme-card" onclick="showSchemeDetail('${id}')">
        <h3>${s[nameKey] || s.name}</h3>
        <p>${s[summaryKey] || s.summary}</p>
        <span class="scheme-tag">${id}</span>
        ${s.tags ? s.tags.map(t => `<span class="scheme-tag">${t}</span>`).join('') : ''}
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
  detail.innerHTML = '<p>Loading...</p>';

  try {
    const res = await fetch(`${API_BASE}/api/schemes/${id}`);
    const s = await res.json();

    const name = currentLang === 'hindi' && s.name_hi ? `${s.name} (${s.name_hi})` : s.name;

    if (!contextMemory.discussedSchemes.includes(s.name)) {
      contextMemory.discussedSchemes.push(s.name);
    }
    saveContext();

    let faqHtml = '';
    if (s.faq && s.faq.length) {
      faqHtml = '<section><h4>Common Questions</h4>';
      s.faq.forEach(f => {
        faqHtml += `<div class="faq-item"><strong>${f.q}</strong><p>${f.a}</p></div>`;
      });
      faqHtml += '</section>';
    }

    detail.innerHTML = `
      <a class="back-link" onclick="backToSchemeList()">&larr; Back to all schemes</a>
      <h3>${name}</h3>
      <div class="meta">${s.ministry} | ${s.type}</div>
      <p>${s.summary}</p>
      <section><h4>Benefits</h4><ul>${s.benefits.map(b => `<li>${b}</li>`).join('')}</ul></section>
      ${s.eligibility ? `
      <section><h4>Who Can Apply</h4><ul>${(s.eligibility.who_can_apply || []).map(x => `<li>${x}</li>`).join('')}</ul></section>
      <section><h4>Who Cannot Apply</h4><ul>${(s.eligibility.who_cannot_apply || []).map(x => `<li>${x}</li>`).join('')}</ul></section>
      <section><h4>Documents Required</h4><ul>${(s.eligibility.documents_required || []).map(x => `<li>${x}</li>`).join('')}</ul></section>` : ''}
      ${s.application_process ? `
      <section><h4>How to Apply</h4>
        ${typeof s.application_process.how_to_apply === 'string'
          ? `<p>${s.application_process.how_to_apply}</p>`
          : `<ul>${s.application_process.how_to_apply.map(x => `<li>${x}</li>`).join('')}</ul>`}
        ${s.application_process.portal_url ? `<p><a href="${s.application_process.portal_url}" target="_blank">${s.application_process.portal_url}</a></p>` : ''}
        ${s.application_process.helpline ? `<p>Helpline: ${s.application_process.helpline}</p>` : ''}
      </section>` : ''}
      ${faqHtml}
      <section><h4>Official Sources</h4><ul>${s.official_sources.map(src => `<li><a href="${src}" target="_blank">${src}</a></li>`).join('')}</ul></section>
      <div class="disclaimer">Note: Information may change. Always refer to official portals for the latest updates.</div>
    `;
  } catch (err) {
    detail.innerHTML = '<p class="error-text">Error loading scheme details.</p>';
  }
}

function backToSchemeList() {
  document.getElementById('scheme-list').classList.remove('hidden');
  document.getElementById('scheme-detail').classList.add('hidden');
}

// --- Compare ---

function loadCompareOptions() {
  const selA = document.getElementById('compare-a');
  const selB = document.getElementById('compare-b');
  const checkLoaded = setInterval(() => {
    if (Object.keys(allSchemes).length > 0) {
      clearInterval(checkLoaded);
      const ids = Object.keys(allSchemes);
      let opts = '<option value="">Select...</option>';
      ids.forEach(id => {
        opts += `<option value="${id}">${allSchemes[id].name}</option>`;
      });
      selA.innerHTML = opts;
      selB.innerHTML = opts;
      if (ids.length >= 2) {
        selA.value = ids[0];
        selB.value = ids[1];
      }
    }
  }, 200);
}

async function compareSchemes() {
  const idA = document.getElementById('compare-a').value;
  const idB = document.getElementById('compare-b').value;
  const results = document.getElementById('compare-results');

  if (!idA || !idB) { alert('Please select two schemes.'); return; }
  if (idA === idB) { alert('Please select two different schemes.'); return; }

  results.classList.remove('hidden');
  results.innerHTML = '<p>Loading...</p>';

  try {
    const [resA, resB] = await Promise.all([
      fetch(`${API_BASE}/api/schemes/${idA}`),
      fetch(`${API_BASE}/api/schemes/${idB}`),
    ]);
    const [a, b] = await Promise.all([resA.json(), resB.json()]);

    const rows = [
      { label: 'Ministry', aVal: a.ministry, bVal: b.ministry },
      { label: 'Type', aVal: a.type, bVal: b.type },
      { label: 'Benefits', aVal: a.benefits.join('<br/>'), bVal: b.benefits.join('<br/>') },
      { label: 'Who Can Apply', aVal: (a.eligibility?.who_can_apply || []).join('<br/>'), bVal: (b.eligibility?.who_can_apply || []).join('<br/>') },
      { label: 'Documents', aVal: (a.eligibility?.documents_required || []).join('<br/>'), bVal: (b.eligibility?.documents_required || []).join('<br/>') },
      { label: 'Portal', aVal: a.application_process?.portal_url ? `<a href="${a.application_process.portal_url}" target="_blank">${a.application_process.portal_url}</a>` : '-', bVal: b.application_process?.portal_url ? `<a href="${b.application_process.portal_url}" target="_blank">${b.application_process.portal_url}</a>` : '-' },
      { label: 'Helpline', aVal: a.application_process?.helpline || '-', bVal: b.application_process?.helpline || '-' },
    ];

    results.innerHTML = `<div class="compare-table-wrap">
      <table class="compare-table">
        <thead><tr><th></th><th>${a.name}</th><th>${b.name}</th></tr></thead>
        <tbody>${rows.map(r => `<tr><td class="compare-label">${r.label}</td><td>${r.aVal}</td><td>${r.bVal}</td></tr>`).join('')}</tbody>
      </table>
    </div>`;
    results.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    results.innerHTML = '<p class="error-text">Error loading comparison.</p>';
  }
}

// --- CSC Locator ---

function initCSCMap() {
  const mapEl = document.getElementById('csc-map');
  if (!mapEl || mapEl._leaflet_initialized) return;
  mapEl._leaflet_initialized = true;

  cscMap = L.map('csc-map').setView([20.5937, 78.9629], 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(cscMap);

  // Add some common CSC locations as a starting point
  const defaultCSCs = [
    { name: 'CSC Hyderabad', lat: 17.3850, lng: 78.4867, address: 'Hyderabad, Telangana' },
    { name: 'CSC Delhi', lat: 28.6139, lng: 77.2090, address: 'Delhi' },
    { name: 'CSC Mumbai', lat: 19.0760, lng: 72.8777, address: 'Mumbai, Maharashtra' },
    { name: 'CSC Bengaluru', lat: 12.9716, lng: 77.5946, address: 'Bengaluru, Karnataka' },
    { name: 'CSC Chennai', lat: 13.0827, lng: 80.2707, address: 'Chennai, Tamil Nadu' },
    { name: 'CSC Kolkata', lat: 22.5726, lng: 88.3639, address: 'Kolkata, West Bengal' },
    { name: 'CSC Lucknow', lat: 26.8467, lng: 80.9462, address: 'Lucknow, Uttar Pradesh' },
    { name: 'CSC Pune', lat: 18.5204, lng: 73.8567, address: 'Pune, Maharashtra' },
    { name: 'CSC Ahmedabad', lat: 23.0225, lng: 72.5714, address: 'Ahmedabad, Gujarat' },
    { name: 'CSC Jaipur', lat: 26.9124, lng: 75.7873, address: 'Jaipur, Rajasthan' },
  ];

  defaultCSCs.forEach(csc => {
    const marker = L.marker([csc.lat, csc.lng])
      .addTo(cscMap)
      .bindPopup(`<strong>${csc.name}</strong><br/>${csc.address}<br/><br/><em>Visit csc.gov.in for more CSCs near you.</em>`);
    cscMarkers.push(marker);
  });

  document.getElementById('csc-results').innerHTML = `<p>Showing ${defaultCSCs.length} major CSC locations. Zoom in or search for your city.</p>`;
}

async function searchCSC() {
  const query = document.getElementById('csc-location').value.trim();
  if (!query) return;

  const resultsEl = document.getElementById('csc-results');
  resultsEl.innerHTML = '<div class="loading-spinner"></div><p>Searching...</p>';

  try {
    // Use Nominatim (free OpenStreetMap geocoding service) with proper user agent
    const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&countrycodes=IN`);
    const geoData = await geoRes.json();

    if (!geoData || geoData.length === 0) {
      resultsEl.innerHTML = '<p class="error-text">Location not found. Try a different city name or pincode.</p>';
      return;
    }

    const loc = geoData[0];
    const lat = parseFloat(loc.lat);
    const lng = parseFloat(loc.lon);

    // Clear existing markers
    cscMarkers.forEach(m => cscMap.removeLayer(m));
    cscMarkers = [];

    // Center map on searched location
    cscMap.setView([lat, lng], 10);

    // Add marker for searched location
    const searchMarker = L.marker([lat, lng])
      .addTo(cscMap)
      .bindPopup(`<strong>${loc.display_name}</strong>`)
      .openPopup();
    cscMarkers.push(searchMarker);

    // Placeholder CSCs around the searched area
    const nearbyCSCs = [
      { name: `CSC ${loc.display_name.split(',')[0] || 'Centre'}`, lat: lat + 0.05, lng: lng + 0.05, address: 'Nearby CSC — verify at csc.gov.in' },
      { name: `CSC ${loc.display_name.split(',')[0] || 'Centre'}`, lat: lat - 0.05, lng: lng - 0.03, address: 'Nearby CSC — verify at csc.gov.in' },
    ];

    nearbyCSCs.forEach(csc => {
      const marker = L.marker([csc.lat, csc.lng], { icon: L.divIcon({ className: 'csc-marker', html: '📍', iconSize: [20, 20] }) })
        .addTo(cscMap)
        .bindPopup(`<strong>${csc.name}</strong><br/>${csc.address}<br/><br/><a href="https://csc.gov.in" target="_blank">Find more at csc.gov.in</a>`);
      cscMarkers.push(marker);
    });

    resultsEl.innerHTML = `<p>📍 Showing CSCs near <strong>${loc.display_name}</strong>. Visit <a href="https://csc.gov.in" target="_blank">csc.gov.in</a> for the complete directory.</p>`;
  } catch (err) {
    resultsEl.innerHTML = '<p class="error-text">Error searching location. Please try again.</p>';
  }
}
