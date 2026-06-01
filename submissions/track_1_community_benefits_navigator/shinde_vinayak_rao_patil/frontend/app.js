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
const CONTEXT_KEY = 'cb_context_memory';
const SESSION_KEY = 'cb_session_id';
const DARK_KEY = 'cb_dark_mode';

let currentSessionId;
try {
  currentSessionId = getSessionId();
} catch (e) {
  currentSessionId = 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
  try { localStorage.setItem(SESSION_KEY, currentSessionId); } catch (_) {}
}

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
      <strong>${t('welcome_title')}</strong><br/>
      ${t('welcome_text')}<br/><br/>
      <strong>${t('welcome_try_asking')}</strong>
      <ul>
        <li>${t('welcome_example_1')}</li>
        <li>${t('welcome_example_2')}</li>
        <li>${t('welcome_example_3')}</li>
      </ul>
      <div class="disclaimer">${t('disclaimer_ai_generated')}</div>
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
    sep.innerHTML = `<div class="bubble" style="font-size:0.78rem;color:var(--text-secondary);text-align:center;background:transparent;border:none;">${t('previous_conversation_restored')} (${restored}${t('messages_suffix')}) —</div>`;
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
  document.querySelector('html').setAttribute('lang', currentLang === 'hindi' ? 'hi' : 'en');
}

const LANG_NAMES = {
  english: 'English', hindi: 'हिन्दी', telugu: 'తెలుగు',
  tamil: 'தமிழ்', bengali: 'বাংলা', marathi: 'मराठी',
};

const UI = {
  sidebar_title: { english: 'Chat History', hindi: 'चैट इतिहास' },
  sidebar_new_chat: { english: '+ New Chat', hindi: '+ नया चैट' },
  sidebar_search_placeholder: { english: 'Search conversations...', hindi: 'बातचीत खोजें...' },
  sidebar_no_conversations: { english: 'No conversations yet', hindi: 'अभी तक कोई बातचीत नहीं' },
  group_today: { english: 'Today', hindi: 'आज' },
  group_yesterday: { english: 'Yesterday', hindi: 'कल' },
  group_week: { english: 'Last 7 Days', hindi: 'पिछले 7 दिन' },
  group_older: { english: 'Earlier', hindi: 'पुराने' },
  new_chat_title: { english: 'New Chat', hindi: 'नया चैट' },
  tab_chat: { english: 'Chat', hindi: 'चैट' },
  tab_eligibility: { english: 'Eligibility', hindi: 'पात्रता' },
  tab_schemes: { english: 'Schemes', hindi: 'योजनाएं' },
  tab_compare: { english: 'Compare', hindi: 'तुलना' },
  tab_csc: { english: 'CSC Locator', hindi: 'CSC लोकेटर' },
  send_btn: { english: 'Send', hindi: 'भेजें' },
  new_btn: { english: 'New', hindi: 'नया' },
  confidence_label: { english: 'Confidence', hindi: 'विश्वसनीयता' },
  voice_not_supported: { english: 'Voice input is not supported in this browser. Try Chrome or Edge.', hindi: 'वॉइस इनपुट इस ब्राउज़र में समर्थित नहीं है। क्रोम या एज का उपयोग करें।' },
  voice_error_prefix: { english: 'Voice input error: ', hindi: 'वॉइस इनपुट त्रुटि: ' },
  rate_limit_error: { english: 'Rate limit exceeded. Please wait a moment.', hindi: 'दर सीमा पार हो गई। कृपया एक क्षण प्रतीक्षा करें।' },
  generic_error_prefix: { english: 'Error: ', hindi: 'त्रुटि: ' },
  generic_error_suffix: { english: '. Please check that the backend is running.', hindi: '. कृपया जांचें कि बैकएंड चल रहा है।' },
  suggested_questions_label: { english: 'You might also ask:', hindi: 'आप यह भी पूछ सकते हैं:' },
  welcome_title: { english: 'Welcome.', hindi: 'स्वागत है।' },
  welcome_text: { english: 'I can help you find and apply for Indian government welfare schemes.', hindi: 'मैं आपको भारत सरकार की कल्याणकारी योजनाओं को खोजने और आवेदन करने में मदद कर सकता हूं।' },
  welcome_try_asking: { english: 'Try asking:', hindi: 'पूछने का प्रयास करें:' },
  welcome_example_1: { english: '"What schemes am I eligible for?"', hindi: '"मैं किन योजनाओं के लिए पात्र हूं?"' },
  welcome_example_2: { english: '"How to apply for PM-KISAN?"', hindi: '"PM-KISAN के लिए आवेदन कैसे करें?"' },
  welcome_example_3: { english: '"Documents needed for Ayushman Bharat"', hindi: '"Ayushman Bharat के लिए आवश्यक दस्तावेज"' },
  chat_input_placeholder: { english: 'Type your question here...', hindi: 'अपना प्रश्न यहां टाइप करें...' },
  disclaimer_ai_generated: { english: 'Note: AI-generated — always verify with official sources', hindi: 'नोट: AI-जनित — हमेशा आधिकारिक स्रोतों से सत्यापित करें' },
  disclaimer_estimate: { english: 'Note: This is an estimate based on limited information. Visit official portals for confirmation.', hindi: 'नोट: यह सीमित जानकारी पर आधारित अनुमान है। पुष्टि के लिए आधिकारिक पोर्टल देखें।' },
  disclaimer_info_may_change: { english: 'Note: Information may change. Always refer to official portals for the latest updates.', hindi: 'नोट: जानकारी बदल सकती है। नवीनतम जानकारी के लिए हमेशा आधिकारिक पोर्टल देखें।' },
  check_eligibility_btn: { english: 'Check Eligibility', hindi: 'पात्रता जांचें' },
  checking_btn: { english: 'Checking...', hindi: 'जांच हो रही है...' },
  checking_eligibility: { english: 'Checking eligibility...', hindi: 'पात्रता जांची जा रही है...' },
  eligibility_results_title: { english: 'Eligibility Results', hindi: 'पात्रता परिणाम' },
  download_pdf: { english: 'Download PDF Report', hindi: 'PDF रिपोर्ट डाउनलोड करें' },
  schemes_qualified: { english: 'Schemes You May Qualify For', hindi: 'योजनाएं जिनके लिए आप पात्र हो सकते हैं' },
  may_not_qualify: { english: 'May Not Qualify', hindi: 'पात्र नहीं हो सकते' },
  likely_eligible: { english: 'Likely Eligible', hindi: 'संभावित रूप से पात्र' },
  match_confidence: { english: 'Match confidence: ', hindi: 'मिलान विश्वसनीयता: ' },
  explain_with_ai: { english: 'Explain with AI', hindi: 'AI से स्पष्टीकरण' },
  generating_ai_explanation: { english: 'Generating AI explanation...', hindi: 'AI स्पष्टीकरण तैयार हो रहा है...' },
  best_scheme_label: { english: 'Best Scheme:', hindi: 'सर्वश्रेष्ठ योजना:' },
  next_steps: { english: 'Next Steps', hindi: 'अगले कदम' },
  improvement_tips: { english: 'Improvement Tips', hindi: 'सुधार के सुझाव' },
  error_checking_eligibility: { english: 'Error checking eligibility. Is the backend running?', hindi: 'पात्रता जांचने में त्रुटि। क्या बैकएंड चल रहा है?' },
  error_generating_explanation: { english: 'Error generating AI explanation.', hindi: 'AI स्पष्टीकरण तैयार करने में त्रुटि।' },
  age_label: { english: 'Age', hindi: 'आयु' },
  income_label: { english: 'Annual Family Income (INR)', hindi: 'वार्षिक पारिवारिक आय (INR)' },
  occupation_label: { english: 'Occupation', hindi: 'व्यवसाय' },
  gender_label: { english: 'Gender', hindi: 'लिंग' },
  select_option: { english: 'Select...', hindi: 'चुनें...' },
  farmer: { english: 'Farmer', hindi: 'किसान' },
  daily_wage: { english: 'Daily Wage Worker', hindi: 'दिहाड़ी मजदूर' },
  government_employee: { english: 'Government Employee', hindi: 'सरकारी कर्मचारी' },
  private_sector: { english: 'Private Sector', hindi: 'निजी क्षेत्र' },
  student: { english: 'Student', hindi: 'छात्र' },
  unemployed: { english: 'Unemployed', hindi: 'बेरोजगार' },
  retired: { english: 'Retired', hindi: 'सेवानिवृत्त' },
  other_occupation: { english: 'Other', hindi: 'अन्य' },
  male: { english: 'Male', hindi: 'पुरुष' },
  female: { english: 'Female', hindi: 'महिला' },
  other_gender: { english: 'Other', hindi: 'अन्य' },
  landowner_label: { english: 'I own agricultural land', hindi: 'मेरे पास कृषि भूमि है' },
  student_label: { english: 'I am a student', hindi: 'मैं एक छात्र हूं' },
  has_lpg_label: { english: 'I already have an LPG connection', hindi: 'मेरे पास पहले से LPG कनेक्शन है' },
  owns_house_label: { english: 'My family owns a pucca house', hindi: 'मेरे परिवार के पास पक्का मकान है' },
  supported_schemes: { english: 'Supported Schemes', hindi: 'समर्थित योजनाएं' },
  search_schemes_placeholder: { english: 'Search schemes...', hindi: 'योजनाएं खोजें...' },
  no_schemes_match: { english: 'No schemes match your search.', hindi: 'आपकी खोज से मेल खाने वाली कोई योजना नहीं है।' },
  loading: { english: 'Loading...', hindi: 'लोड हो रहा है...' },
  scheme_detail_loading: { english: 'Loading...', hindi: 'लोड हो रहा है...' },
  back_to_all_schemes: { english: 'Back to all schemes', hindi: 'सभी योजनाओं पर वापस जाएं' },
  benefits_label: { english: 'Benefits', hindi: 'लाभ' },
  who_can_apply_label: { english: 'Who Can Apply', hindi: 'कौन आवेदन कर सकता है' },
  who_cannot_apply_label: { english: 'Who Cannot Apply', hindi: 'कौन आवेदन नहीं कर सकता' },
  documents_required_label: { english: 'Documents Required', hindi: 'आवश्यक दस्तावेज' },
  how_to_apply_label: { english: 'How to Apply', hindi: 'आवेदन कैसे करें' },
  common_questions_label: { english: 'Common Questions', hindi: 'सामान्य प्रश्न' },
  official_sources_label: { english: 'Official Sources', hindi: 'आधिकारिक स्रोत' },
  helpline_label: { english: 'Helpline: ', hindi: 'हेल्पलाइन: ' },
  error_loading_scheme: { english: 'Error loading scheme details.', hindi: 'योजना विवरण लोड करने में त्रुटि।' },
  compare_schemes: { english: 'Compare Schemes', hindi: 'योजनाओं की तुलना करें' },
  compare_description: { english: 'Select two schemes to compare side-by-side.', hindi: 'तुलना करने के लिए दो योजनाएं चुनें।' },
  scheme_a: { english: 'Scheme A', hindi: 'योजना A' },
  scheme_b: { english: 'Scheme B', hindi: 'योजना B' },
  compare_btn: { english: 'Compare', hindi: 'तुलना करें' },
  ai_compare_btn: { english: 'AI Compare', hindi: 'AI तुलना' },
  select_two_schemes: { english: 'Please select two schemes.', hindi: 'कृपया दो योजनाएं चुनें।' },
  select_different_schemes: { english: 'Please select two different schemes.', hindi: 'कृपया दो अलग-अलग योजनाएं चुनें।' },
  ai_comparison: { english: 'AI Comparison', hindi: 'AI तुलना' },
  key_differences: { english: 'Key Differences', hindi: 'मुख्य अंतर' },
  recommendation_label: { english: 'Recommendation:', hindi: 'सिफारिश:' },
  can_apply_both_label: { english: 'Can apply to both?', hindi: 'दोनों के लिए आवेदन कर सकते हैं?' },
  yes: { english: 'Yes', hindi: 'हां' },
  no: { english: 'No', hindi: 'नहीं' },
  generating_ai_comparison: { english: 'Generating AI comparison...', hindi: 'AI तुलना तैयार हो रही है...' },
  error_generating_comparison: { english: 'Error generating AI comparison.', hindi: 'AI तुलना तैयार करने में त्रुटि।' },
  error_loading_comparison: { english: 'Error loading comparison.', hindi: 'तुलना लोड करने में त्रुटि।' },
  ministry_col: { english: 'Ministry', hindi: 'मंत्रालय' },
  type_col: { english: 'Type', hindi: 'प्रकार' },
  benefits_col: { english: 'Benefits', hindi: 'लाभ' },
  who_can_apply_col: { english: 'Who Can Apply', hindi: 'कौन आवेदन कर सकता है' },
  documents_col: { english: 'Documents', hindi: 'दस्तावेज' },
  portal_col: { english: 'Portal', hindi: 'पोर्टल' },
  helpline_col: { english: 'Helpline', hindi: 'हेल्पलाइन' },
  csc_locator_title: { english: 'CSC Locator', hindi: 'CSC लोकेटर' },
  csc_description: { english: 'Find Common Service Centres (CSCs) near you for help with scheme applications.', hindi: 'योजना आवेदनों में सहायता के लिए अपने निकट सामान्य सेवा केंद्र (CSC) खोजें।' },
  csc_location_label: { english: 'Enter your city or pincode', hindi: 'अपना शहर या पिनकोड दर्ज करें' },
  csc_location_placeholder: { english: 'e.g. Hyderabad, 500001', hindi: 'जैसे हैदराबाद, 500001' },
  search_btn: { english: 'Search', hindi: 'खोजें' },
  location_not_found: { english: 'Location not found. Try a different city name or pincode.', hindi: 'स्थान नहीं मिला। कोई दूसरा शहर या पिनकोड आज़माएं।' },
  showing_csc_near: { english: 'Showing CSCs near ', hindi: 'के निकट CSC दिखाए जा रहे हैं ' },
  error_searching_location: { english: 'Error searching location. Please try again.', hindi: 'स्थान खोजने में त्रुटि। कृपया पुनः प्रयास करें।' },
  csc_verify: { english: 'Nearby CSC — verify at csc.gov.in', hindi: 'निकटतम CSC — csc.gov.in पर सत्यापित करें' },
  csc_find_more: { english: 'Find more at csc.gov.in', hindi: 'csc.gov.in पर और खोजें' },
  footer_text: { english: 'Powered by NVIDIA Nemotron-3-Super | Built for HydPy Community Contest 2026', hindi: 'NVIDIA Nemotron-3-Super द्वारा संचालित | HydPy Community Contest 2026 के लिए बनाया गया' },
  footer_disclaimer: { english: 'Note: This is an AI assistant. Always verify information with official government portals and CSC centres.', hindi: 'नोट: यह एक AI सहायक है। हमेशा आधिकारिक सरकारी पोर्टल और CSC केंद्रों से जानकारी सत्यापित करें।' },
  previous_conversation_restored: { english: '— Previous conversation restored', hindi: '— पिछली बातचीत पुनर्स्थापित की गई' },
  searching: { english: 'Searching...', hindi: 'खोज हो रही है...' },
  delete_confirm: { english: 'Delete this conversation permanently?', hindi: 'इस बातचीत को स्थायी रूप से हटाएं?' },
  clear_confirm: { english: 'Start a new conversation? The current one will be saved.', hindi: 'नई बातचीत शुरू करें? वर्तमान बातचीत सहेजी जाएगी।' },
  rename_prompt: { english: 'Rename conversation:', hindi: 'बातचीत का नाम बदलें:' },
  high_confidence: { english: 'High confidence', hindi: 'उच्च विश्वसनीयता' },
  medium_confidence: { english: 'Medium confidence — verify with official sources', hindi: 'मध्यम विश्वसनीयता — आधिकारिक स्रोतों से सत्यापित करें' },
  low_confidence: { english: 'Low confidence — please verify thoroughly', hindi: 'कम विश्वसनीयता — कृपया अच्छी तरह सत्यापित करें' },
  messages_suffix: { english: ' msgs', hindi: ' संदेश' },
  csc_results_info: { english: 'Showing ', hindi: 'दिखाए जा रहे हैं ' },
  major_csc_locations: { english: ' major CSC locations. Zoom in or search for your city.', hindi: ' प्रमुख CSC स्थान। ज़ूम इन करें या अपना शहर खोजें।' },
  age_placeholder: { english: 'e.g. 35', hindi: 'जैसे 35' },
  income_placeholder: { english: 'e.g. 200000', hindi: 'जैसे 200000' },
  app_title: { english: 'Community Benefits Navigator', hindi: 'सामुदायिक लाभ नेविगेटर' },
  compare_hint: { english: 'Table compare shows side-by-side facts. AI Compare generates a personalized LLM-powered comparison with recommendations.', hindi: 'तालिका तुलना तथ्यों को एक साथ दिखाती है। AI Compare सिफारिशों के साथ वैयक्तिकृत तुलना उत्पन्न करता है।' },
  tab_schemes_info: { english: 'Browse/search all available schemes. Click any scheme to see full details — benefits, eligibility, required documents, portal link, and helpline.', hindi: 'सभी उपलब्ध योजनाओं को ब्राउज़/खोजें। पूर्ण विवरण देखने के लिए किसी भी योजना पर क्लिक करें — लाभ, पात्रता, आवश्यक दस्तावेज, पोर्टल लिंक और हेल्पलाइन।' },
  tab_compare_info: { english: 'Pick two schemes, then click Compare for a side-by-side facts table, or AI Compare for a Nemotron-generated personalized comparison with recommendations.', hindi: 'दो योजनाएं चुनें, फिर तुलना के लिए Compare बटन या Nemotron-जनित वैयक्तिकृत तुलना के लिए AI Compare बटन पर क्लिक करें।' },
};

function t(key) {
  if (UI[key] && UI[key][currentLang]) return UI[key][currentLang];
  if (UI[key] && UI[key].english) return UI[key].english;
  return key;
}

function translateStaticUI() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t(key);
  });

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

  document.title = t('app_title');
}

function applyLangUI() {
  translateStaticUI();
  filterSchemes();
  document.querySelector('html').setAttribute('lang', currentLang === 'hindi' ? 'hi' : 'en');
}

function setLang(value) {
  currentLang = value;
  localStorage.setItem('lang', value);
  applyLangUI();
  document.querySelector('html').setAttribute('lang', currentLang === 'hindi' ? 'hi' : 'en');
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
  if (tab === 'csc') setTimeout(initCSCMap, 200);
  if (tab === 'compare') refreshCompareDropdowns();
}

function clearChat() {
  if (!confirm(t('clear_confirm'))) return;
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

function groupLabel(key) {
  return UI[key] && (UI[key][currentLang] || UI[key].english) ? (UI[key][currentLang] || UI[key].english) : key;
}

function renderSidebar() {
  const list = document.getElementById('sidebar-list');
  const q = (document.getElementById('sidebar-search').value || '').toLowerCase();
  const filtered = q ? sessionsList.filter(s => (s.title || '').toLowerCase().includes(q)) : sessionsList;

  if (!filtered.length) {
    list.innerHTML = `<p class="sidebar-empty">${t('sidebar_no_conversations')}</p>`;
    return;
  }

  const groups = groupSessions(filtered);
  let html = '';
  ['today', 'yesterday', 'week', 'older'].forEach(key => {
    if (!groups[key].length) return;
    html += `<div class="sidebar-group-label">${groupLabel('group_' + key)}</div>`;
    groups[key].forEach(s => {
      const isActive = s.id === currentSessionId;
      const title = s.title || t('new_chat_title');
      const date = new Date(s.updated_at * 1000);
      const dateStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      const timeStr = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
      const isToday = s.updated_at >= new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()).getTime() / 1000;

      html += `
        <div class="session-card ${isActive ? 'active' : ''}" onclick="switchSession('${s.id}')">
          <div class="session-card-main">
            <div class="session-title">${escHtml(title)}</div>
            <div class="session-meta">${isToday ? timeStr : dateStr + ' ' + timeStr} · ${s.message_count}${t('messages_suffix')}</div>
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
  if (!confirm(t('delete_confirm'))) return;
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
  const currentTitle = session ? (session.title || t('new_chat_title')) : t('new_chat_title');
  const newTitle = prompt(t('rename_prompt'), currentTitle);
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
    addMessage(t('voice_not_supported'), 'bot', null, null, true);
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
      document.getElementById('mic-btn').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
    };

    recognition.onerror = (event) => {
      isListening = false;
      document.getElementById('mic-btn').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        addMessage(t('voice_error_prefix') + event.error, 'bot', null, null, true);
      }
    };

    recognition.onend = () => {
      isListening = false;
      document.getElementById('mic-btn').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
    };
  }

  recognition.lang = { english: 'en-IN', hindi: 'hi-IN', telugu: 'te-IN', tamil: 'ta-IN', bengali: 'bn-IN', marathi: 'mr-IN' }[currentLang] || 'en-IN';
  recognition.start();
  isListening = true;
  document.getElementById('mic-btn').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" fill="#ef4444"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
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
      if (res.status === 429) throw new Error(t('rate_limit_error'));
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    removeTyping();
    addMessage(data.reply, 'bot', data.citations, data.confidence, true);

    if (data.suggested_questions && data.suggested_questions.length > 0) {
      displaySuggestedQuestions(data.suggested_questions);
    }

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
    addMessage(t('generic_error_prefix') + err.message + t('generic_error_suffix'), 'bot', null, null, true);
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
    html += `<div class="disclaimer">${t('disclaimer_ai_generated')}</div>`;
  }

  html += '</div>';
  div.innerHTML = html;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function displaySuggestedQuestions(questions) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message bot suggested-questions';
  let html = `<div class="bubble"><div class="sq-label">${t('suggested_questions_label')}</div><div class="sq-chips">`;
  questions.forEach(q => {
    html += `<button class="sq-chip" onclick="askSuggested('${encodeURIComponent(q)}')">${escHtml(q)}</button>`;
  });
  html += '</div></div>';
  div.innerHTML = html;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function askSuggested(encoded) {
  const question = decodeURIComponent(encoded);
  document.getElementById('chat-input').value = question;
  autoResize(document.getElementById('chat-input'));
  sendMessage();
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
  const pct = (confidence * 100).toFixed(0);
  if (confidence > 0.6) {
    dot.classList.add('high');
    label.textContent = `${t('high_confidence')} (${pct}%)`;
  } else if (confidence > 0.3) {
    dot.classList.add('med');
    label.textContent = `${t('medium_confidence')} (${pct}%)`;
  } else {
    dot.classList.add('low');
    label.textContent = `${t('low_confidence')} (${pct}%)`;
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
  btn.textContent = t('checking_btn');

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
  resultsDiv.innerHTML = `<div class="loading-spinner"></div><p>${t('checking_eligibility')}</p>`;

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
    html += `<div class="report-actions"><h3>${t('eligibility_results_title')}</h3><button class="btn-small" onclick="downloadPDF()">${t('download_pdf')}</button></div>`;

    const matched = data.filter(s => s.match);
    const notMatched = data.filter(s => !s.match);

    if (matched.length > 0) {
      html += `<h4 style="color:var(--success);margin:12px 0 8px;">${t('schemes_qualified')}</h4>`;
    }

    const sorted = [...matched, ...notMatched];
    sorted.forEach(s => {
      const isMatch = s.match;
      html += `
        <div class="result-card ${isMatch ? 'result-match' : 'result-no-match'}">
          <div class="result-header">
            <h3>${s.name}</h3>
            <div class="match-badge match-${isMatch}">${isMatch ? t('likely_eligible') : t('may_not_qualify')}</div>
          </div>
          <div class="confidence-bar"><div class="confidence-fill" style="width:${s.confidence * 100}%"></div></div>
          <div class="confidence-text">${t('match_confidence')}${(s.confidence * 100).toFixed(0)}%</div>
          ${s.reasons.length ? `<div class="reasons">${s.reasons.join('; ')}</div>` : ''}
        </div>
      `;
    });

    html += '</div>';
    html += `<div class="disclaimer" style="margin-top:12px">${t('disclaimer_estimate')}</div>`;
    html += `<button class="btn-primary" style="margin-top:16px" onclick="explainEligibility()">${t('explain_with_ai')}</button>`;
    resultsDiv.innerHTML = html;
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    resultsDiv.innerHTML = `<p class="error-text">${t('error_checking_eligibility')}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = t('check_eligibility_btn');
  }
}

async function explainEligibility() {
  const profile = contextMemory.userProfile;
  const results = contextMemory.eligibilityResults;
  if (!results || !results.length) return;

  const explainDiv = document.getElementById('eligibility-explanation');
  explainDiv.classList.remove('hidden');
  explainDiv.innerHTML = `<div class="loading-spinner"></div><p>${t('generating_ai_explanation')}</p>`;

  try {
    const res = await fetch(`${API_BASE}/api/eligibility/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile,
        results: results.map(r => ({
          scheme_id: r.scheme_id,
          name: r.name,
          confidence: r.confidence,
          match: r.match,
          reasons: [],
        })),
        language: currentLang,
      }),
    });
    const data = await res.json();
    let html = '<div class="explain-panel">';
    html += `<h3>${t('ai_comparison')}</h3>`;
    html += `<p>${formatText(data.explanation || '')}</p>`;
    if (data.best_scheme) {
      html += `<div class="best-scheme"><strong>${t('best_scheme_label')}</strong> ${data.best_scheme}</div>`;
    }
    if (data.next_steps && data.next_steps.length) {
      html += `<h4>${t('next_steps')}</h4><ul>` + data.next_steps.map(s => `<li>${escHtml(s)}</li>`).join('') + '</ul>';
    }
    if (data.improvement_tips && data.improvement_tips.length) {
      html += `<h4>${t('improvement_tips')}</h4><ul>` + data.improvement_tips.map(t => `<li>${escHtml(t)}</li>`).join('') + '</ul>';
    }
    html += '</div>';
    explainDiv.innerHTML = html;
    explainDiv.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    explainDiv.innerHTML = `<p class="error-text">${t('error_generating_explanation')}</p>`;
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
    refreshCompareDropdowns();
  } catch (err) {
    document.getElementById('scheme-list').innerHTML = `<p class="error-text">${t('error_checking_eligibility')}</p>`;
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
  list.innerHTML = html || `<p>${t('no_schemes_match')}</p>`;
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
  detail.innerHTML = `<p>${t('loading')}</p>`;

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
      faqHtml = `<section><h4>${t('common_questions_label')}</h4>`;
      s.faq.forEach(f => {
        faqHtml += `<div class="faq-item"><strong>${f.q}</strong><p>${f.a}</p></div>`;
      });
      faqHtml += '</section>';
    }

    detail.innerHTML = `
      <a class="back-link" onclick="backToSchemeList()">&larr; ${t('back_to_all_schemes')}</a>
      <h3>${name}</h3>
      <div class="meta">${s.ministry} | ${s.type}</div>
      <p>${s.summary}</p>
      <section><h4>${t('benefits_label')}</h4><ul>${s.benefits.map(b => `<li>${b}</li>`).join('')}</ul></section>
      ${s.eligibility ? `
      <section><h4>${t('who_can_apply_label')}</h4><ul>${(s.eligibility.who_can_apply || []).map(x => `<li>${x}</li>`).join('')}</ul></section>
      <section><h4>${t('who_cannot_apply_label')}</h4><ul>${(s.eligibility.who_cannot_apply || []).map(x => `<li>${x}</li>`).join('')}</ul></section>
      <section><h4>${t('documents_required_label')}</h4><ul>${(s.eligibility.documents_required || []).map(x => `<li>${x}</li>`).join('')}</ul></section>` : ''}
      ${s.application_process ? `
      <section><h4>${t('how_to_apply_label')}</h4>
        ${typeof s.application_process.how_to_apply === 'string'
          ? `<p>${s.application_process.how_to_apply}</p>`
          : `<ul>${s.application_process.how_to_apply.map(x => `<li>${x}</li>`).join('')}</ul>`}
        ${s.application_process.portal_url ? `<p><a href="${s.application_process.portal_url}" target="_blank">${s.application_process.portal_url}</a></p>` : ''}
        ${s.application_process.helpline ? `<p>${t('helpline_label')}${s.application_process.helpline}</p>` : ''}
      </section>` : ''}
      ${faqHtml}
      <section><h4>${t('official_sources_label')}</h4><ul>${s.official_sources.map(src => `<li><a href="${src}" target="_blank">${src}</a></li>`).join('')}</ul></section>
      <div class="disclaimer">${t('disclaimer_info_may_change')}</div>
    `;
  } catch (err) {
    detail.innerHTML = `<p class="error-text">${t('error_loading_scheme')}</p>`;
  }
}

function backToSchemeList() {
  document.getElementById('scheme-list').classList.remove('hidden');
  document.getElementById('scheme-detail').classList.add('hidden');
}

// --- Compare ---

function refreshCompareDropdowns() {
  const selA = document.getElementById('compare-a');
  const selB = document.getElementById('compare-b');
  if (!selA) return;
  const ids = Object.keys(allSchemes);
  let opts = `<option value="">${t('select_option')}</option>`;
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

function loadCompareOptions() {
  refreshCompareDropdowns();
}

async function compareSchemes() {
  const idA = document.getElementById('compare-a').value;
  const idB = document.getElementById('compare-b').value;
  const results = document.getElementById('compare-results');

  if (!idA || !idB) { alert(t('select_two_schemes')); return; }
  if (idA === idB) { alert(t('select_different_schemes')); return; }

  document.getElementById('compare-ai-result').classList.add('hidden');
  results.classList.remove('hidden');
  results.innerHTML = `<p>${t('loading')}</p>`;

  try {
    const [resA, resB] = await Promise.all([
      fetch(`${API_BASE}/api/schemes/${idA}`),
      fetch(`${API_BASE}/api/schemes/${idB}`),
    ]);
    const [a, b] = await Promise.all([resA.json(), resB.json()]);

    const rows = [
      { label: t('ministry_col'), aVal: a.ministry, bVal: b.ministry },
      { label: t('type_col'), aVal: a.type, bVal: b.type },
      { label: t('benefits_col'), aVal: a.benefits.join('<br/>'), bVal: b.benefits.join('<br/>') },
      { label: t('who_can_apply_col'), aVal: (a.eligibility?.who_can_apply || []).join('<br/>'), bVal: (b.eligibility?.who_can_apply || []).join('<br/>') },
      { label: t('documents_col'), aVal: (a.eligibility?.documents_required || []).join('<br/>'), bVal: (b.eligibility?.documents_required || []).join('<br/>') },
      { label: t('portal_col'), aVal: a.application_process?.portal_url ? `<a href="${a.application_process.portal_url}" target="_blank">${a.application_process.portal_url}</a>` : '-', bVal: b.application_process?.portal_url ? `<a href="${b.application_process.portal_url}" target="_blank">${b.application_process.portal_url}</a>` : '-' },
      { label: t('helpline_col'), aVal: a.application_process?.helpline || '-', bVal: b.application_process?.helpline || '-' },
    ];

    results.innerHTML = `<div class="compare-table-wrap">
      <table class="compare-table">
        <thead><tr><th></th><th>${a.name}</th><th>${b.name}</th></tr></thead>
        <tbody>${rows.map(r => `<tr><td class="compare-label">${r.label}</td><td>${r.aVal}</td><td>${r.bVal}</td></tr>`).join('')}</tbody>
      </table>
    </div>`;
    results.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    results.innerHTML = `<p class="error-text">${t('error_loading_comparison')}</p>`;
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

  document.getElementById('csc-results').innerHTML = `<p>${t('showing_csc_near')}${defaultCSCs.length}${t('major_csc_locations')}</p>`;
}

async function aiCompareSchemes() {
  const idA = document.getElementById('compare-a').value;
  const idB = document.getElementById('compare-b').value;
  const resultDiv = document.getElementById('compare-ai-result');

  if (!idA || !idB) { alert(t('select_two_schemes')); return; }
  if (idA === idB) { alert(t('select_different_schemes')); return; }

  resultDiv.classList.remove('hidden');
  resultDiv.innerHTML = `<div class="loading-spinner"></div><p>${t('generating_ai_comparison')}</p>`;

  try {
    const res = await fetch(`${API_BASE}/api/eligibility/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scheme_a_id: idA, scheme_b_id: idB, language: currentLang }),
    });
    const data = await res.json();
    let html = '<div class="explain-panel">';
    html += `<h3>${t('ai_comparison')}</h3>`;
    html += `<p>${formatText(data.overall_comparison || '')}</p>`;
    if (data.differences && data.differences.length) {
      html += `<h4>${t('key_differences')}</h4><ul>` + data.differences.map(d => `<li>${escHtml(d)}</li>`).join('') + '</ul>';
    }
    if (data.recommendation) {
      html += `<div class="best-scheme"><strong>${t('recommendation_label')}</strong> ${formatText(data.recommendation)}</div>`;
    }
    html += `<p style="margin-top:8px"><strong>${t('can_apply_both_label')}</strong> ${data.can_apply_both ? t('yes') : t('no')}</p>`;
    html += '</div>';
    resultDiv.innerHTML = html;
    resultDiv.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    resultDiv.innerHTML = `<p class="error-text">${t('error_generating_comparison')}</p>`;
  }
}

async function searchCSC() {
  const query = document.getElementById('csc-location').value.trim();
  if (!query) return;

  const resultsEl = document.getElementById('csc-results');
  resultsEl.innerHTML = `<div class="loading-spinner"></div><p>${t('searching')}</p>`;

  try {
    // Use Nominatim (free OpenStreetMap geocoding service) with proper user agent
    const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5&countrycodes=IN`);
    const geoData = await geoRes.json();

    if (!geoData || geoData.length === 0) {
      resultsEl.innerHTML = `<p class="error-text">${t('location_not_found')}</p>`;
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
      { name: `CSC ${loc.display_name.split(',')[0] || 'Centre'}`, lat: lat + 0.05, lng: lng + 0.05, address: t('csc_verify') },
      { name: `CSC ${loc.display_name.split(',')[0] || 'Centre'}`, lat: lat - 0.05, lng: lng - 0.03, address: t('csc_verify') },
    ];

    nearbyCSCs.forEach(csc => {
      const marker = L.marker([csc.lat, csc.lng], { icon: L.divIcon({ className: 'csc-marker', html: '📍', iconSize: [20, 20] }) })
        .addTo(cscMap)
        .bindPopup(`<strong>${csc.name}</strong><br/>${csc.address}<br/><br/><a href="https://csc.gov.in" target="_blank">${t('csc_find_more')}</a>`);
      cscMarkers.push(marker);
    });

    resultsEl.innerHTML = `<p>📍 ${t('showing_csc_near')}<strong>${loc.display_name}</strong>. ${t('csc_find_more')}.</p>`;
  } catch (err) {
    resultsEl.innerHTML = `<p class="error-text">${t('error_searching_location')}</p>`;
  }
}
