/* ═══════════════════════════════════════════════════════════
   SmartFinance Brain — dashboard.js
   All frontend logic: sidebar, charts, tables, chat, forms
═══════════════════════════════════════════════════════════ */

const API_BASE = '';   // e.g. 'http://localhost:5000' — empty = same origin

// ── STATE ───────────────────────────────────────────────────
let appState = {
  user: null,
  expenses: [],
  expPage: 1,
  expPageSize: 12,
  expFilter: '',
  expCatFilter: '',
  allDashData: null,
  chatMessages: [],
  pendingExpense: null,
  pendingDataset: null,
  sidebarCollapsed: false,
};


// ── THEME-AWARE CHART COLORS ─────────────────────────────────
function getChartTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  return {
    tooltipBg:    isDark ? '#1C2230'                  : '#ffffff',
    tooltipBorder:isDark ? '#21262D'                  : '#e2e8f0',
    titleColor:   isDark ? '#EDF0FF'                  : '#1a202c',
    bodyColor:    isDark ? '#A8B8D8'                  : '#4a5568',
    legendColor:  isDark ? '#C8D5F0'                  : '#374151',
    gridColor:    isDark ? 'rgba(33,38,45,0.6)'       : 'rgba(203,213,225,0.6)',
    tickColor:    isDark ? '#8A9CC4'                  : '#64748b',
    donutBorder:  isDark ? '#0D1117'                  : '#ffffff',
  };
}

// ── CHART INSTANCES ─────────────────────────────────────────
let charts = {};
const C = {
  bg:  'rgba(0,0,0,0)',
  grid: 'rgba(33,38,45,0.8)',
  txt: 'var(--text-muted)',
  colors: ['#4F6EF7','#8B5CF6','#3FB950','#D29922','#F85149','#EC4899','#0EA5E9','#14B8A6'],
};

// ══════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
  // Apply saved theme immediately
  const savedTheme = localStorage.getItem('sfb_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) themeIcon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';

  // Auth guard — check server session
  try {
    const res  = await fetch('/api/dashboard');
    const data = await res.json();
    if (!data.success && res.status === 401) {
      window.location.href = 'login.html';
      return;
    }
    const stored = localStorage.getItem('sfb_user');
    if (stored) {
      appState.user = JSON.parse(stored);
    } else {
      appState.user = { name: 'User', phone: '', email: '' };
    }
  } catch(e) {
    const stored = localStorage.getItem('sfb_user');
    if (!stored) { window.location.href = 'login.html'; return; }
    appState.user = JSON.parse(stored);
  }

  setUserUI();
  setDateHeader();
  setupDragDrop();
  setupSidebarToggle();

  document.getElementById('add-date').value = new Date().toISOString().split('T')[0];

  // Start on AI Assistant page
  navigate('ai');
  setTimeout(loadQuickStatsFull, 500);

  // Run alert check on startup — catches any existing bills due tomorrow/today/overdue
  setTimeout(checkEmailAlerts, 2000);
});

function setUserUI() {
  const u = appState.user;
  const name  = u.name  || 'User';
  const email = u.email || '';
  const initials = name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);

  document.getElementById('sb-name').textContent    = name;
  document.getElementById('sb-email').textContent   = email;
  document.getElementById('sb-avatar').textContent  = initials;
  document.getElementById('header-name').textContent = name.split(' ')[0];
  document.getElementById('header-avatar').textContent = initials;
}

function setDateHeader() {
  const now = new Date();
  document.getElementById('header-month').textContent =
    now.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
}

// ══════════════════════════════════════════════════════════
//  SIDEBAR TOGGLE — FIX: always-visible toggle button
// ══════════════════════════════════════════════════════════
function setupSidebarToggle() {
  // Restore saved state
  const saved = localStorage.getItem('sfb_sidebar');
  if (saved === 'collapsed') collapseSidebar(false);
}

function toggleSidebar() {
  appState.sidebarCollapsed ? expandSidebar() : collapseSidebar();
}

function collapseSidebar(save = true) {
  appState.sidebarCollapsed = true;
  document.getElementById('sidebar').classList.add('collapsed');
  document.getElementById('main-wrap').classList.add('expanded');
  document.getElementById('sb-toggle').classList.add('collapsed');
  document.getElementById('sb-toggle-icon').className = 'fas fa-bars';
  // Show overlay on mobile
  if (window.innerWidth <= 768) {
    document.getElementById('sb-overlay').classList.remove('show');
  }
  if (save) localStorage.setItem('sfb_sidebar', 'collapsed');
}

function expandSidebar() {
  appState.sidebarCollapsed = false;
  document.getElementById('sidebar').classList.remove('collapsed');
  document.getElementById('main-wrap').classList.remove('expanded');
  document.getElementById('sb-toggle').classList.remove('collapsed');
  document.getElementById('sb-toggle-icon').className = 'fas fa-bars';
  if (window.innerWidth <= 768) {
    document.getElementById('sb-overlay').classList.add('show');
  }
  localStorage.setItem('sfb_sidebar', 'expanded');
}

// ══════════════════════════════════════════════════════════
//  NAVIGATION
// ══════════════════════════════════════════════════════════
const pageTitles = {
  ai:        ['AI Assistant',    'Your personal finance AI — ask, upload, take action'],
  expenses:  ['Expenses',        'View, add, import and manage all transactions'],
  budget:    ['Budget & Forecast','Set budgets, track bills, forecast spending'],
  dashboard: ['Dashboard',       'Charts, analytics and financial overview'],
  report:    ['Monthly Report',  'Download PDF · filter by month · full breakdown'],
  files:     ['Imported Files',  'All uploaded files — images, bills, receipts, datasets'],
  settings:  ['Settings',        'AI keys, email alerts, account & security'],
};

function navigate(page) {
  document.querySelectorAll('.sb-nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  document.querySelectorAll('.page').forEach(p => {
    p.classList.toggle('hidden', p.id !== 'page-' + page);
  });
  const [title, sub] = pageTitles[page] || [page, ''];
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-sub').textContent   = sub;

  if (page === 'expenses')  loadExpenses();
  if (page === 'budget')    { loadBudgetPage(); loadBills(); }
  if (page === 'ai')        { setTimeout(() => (typeof loadQuickStatsFull === 'function' ? loadQuickStatsFull() : loadQuickStats()), 0); }
  if (page === 'dashboard') loadDashboard();
  if (page === 'settings')  { loadAccountInfo(); loadSettingsEmailFields(); }
  if (page === 'report')    { setTimeout(loadReport, 50); }
  if (page === 'files')     { setTimeout(loadImportedFiles, 50); }

  if (window.innerWidth <= 768 && !appState.sidebarCollapsed) collapseSidebar();
}

// Budget sub-tab switcher
function budgetTab(t) {
  const tabs = ['overview','bills','forecast','recurring','scenario'];
  document.querySelectorAll('#page-budget .page-tab').forEach((b,i) =>
    b.classList.toggle('active', tabs[i] === t));
  tabs.forEach(id => {
    const el = document.getElementById('btab-' + id);
    if (el) el.classList.toggle('hidden', id !== t);
  });
  if (t === 'forecast')  loadForecastTab();
  if (t === 'recurring') loadRecurringTab();
  if (t === 'scenario')  loadScenarioCategories();
}

// Settings sub-tab switcher
function settingsTab(t) {
  const tabs = ['ai','email','account','danger'];
  document.querySelectorAll('#page-settings .page-tab').forEach((b,i) =>
    b.classList.toggle('active', tabs[i] === t));
  tabs.forEach(id => {
    const el = document.getElementById('stab-' + id);
    if (el) el.classList.toggle('hidden', id !== t);
  });
  if (t === 'email') renderThresholdCheckboxes('threshold-checkboxes-email');
}

// ══════════════════════════════════════════════════════════
//  API HELPERS
// ══════════════════════════════════════════════════════════
async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API_BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`API ${path} failed:`, e.message);
    return null;
  }
}

function fmt(n) {
  if (n === undefined || n === null) return '—';
  return '₹' + parseFloat(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}
function fmtFull(n) {
  return '₹' + parseFloat(n||0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ══════════════════════════════════════════════════════════
//  DASHBOARD DATA
// ══════════════════════════════════════════════════════════
async function loadDashboard() {
  const data = await apiFetch('/api/dashboard');
  if (!data) {
    console.warn('Could not load dashboard data from server. Is server.py running?');
    return;
  }
  appState.allDashData = data;

  // KPIs
  document.getElementById('kpi-alltime').textContent  = fmt(data.all_time_total);
  document.getElementById('kpi-month').textContent    = fmt(data.month_total);
  document.getElementById('kpi-count').textContent    = data.month_count || 0;

  if (data.budget) {
    const left = data.budget - data.month_total;
    const pct  = ((data.month_total / data.budget) * 100).toFixed(1);
    document.getElementById('kpi-budget-left').textContent = fmt(Math.max(0, left));
    const pctEl = document.getElementById('kpi-budget-pct');
    pctEl.textContent = pct + '% used';
    pctEl.className = 'kpi-delta ' + (pct >= 90 ? 'down' : pct >= 70 ? '' : 'up');
  } else {
    document.getElementById('kpi-budget-left').textContent = 'Not set';
  }

  // Month delta
  if (data.prev_total !== undefined) {
    const delta = data.month_total - data.prev_total;
    const pct   = data.prev_total ? Math.abs(delta / data.prev_total * 100).toFixed(1) : 0;
    const el    = document.getElementById('kpi-month-delta');
    el.textContent = (delta >= 0 ? '▲' : '▼') + ' ' + pct + '% vs last month';
    el.className = 'kpi-delta ' + (delta > 0 ? 'down' : 'up');
  }

  // Sidebar mini stats
  document.getElementById('sb-month-total').textContent = fmt(data.month_total);
  if (data.budget) {
    const pct = Math.min((data.month_total / data.budget) * 100, 100);
    document.getElementById('sb-budget-line').textContent = 'of ' + fmt(data.budget);
    document.getElementById('sb-budget-bar').style.width = pct + '%';
    document.getElementById('sb-budget-bar').style.background = pct > 90 ? '#F85149' : pct > 70 ? '#D29922' : '#4F6EF7';
  } else {
    document.getElementById('sb-budget-line').textContent = 'No budget set';
  }

  // Status dots
  // AI status in sidebar
  const aiStatusEl = document.getElementById('sb-ai-status');
  if (aiStatusEl) {
    aiStatusEl.innerHTML = data.groq_active
      ? '<span class="status-dot dot-green"></span><span style="color:#3FB950;">AI: Active</span>'
      : '<span class="status-dot dot-gray"></span><span>AI: Offline</span>';
  }
  // Email status in sidebar
  const emailStatusEl = document.getElementById('sb-email-status');
  if (emailStatusEl) {
    emailStatusEl.innerHTML = data.email_active
      ? '<span class="status-dot dot-green"></span><span style="color:#3FB950;">Email: On</span>'
      : '<span class="status-dot dot-gray"></span><span>Email: Off</span>';
  }
  // Fix badge — stop showing "Connecting..." once dashboard loads
  const badge = document.getElementById('chat-ai-badge');
  if (badge) {
    if (data.groq_active) {
      badge.textContent = 'Connected';
      badge.style.background = 'rgba(16,185,129,0.15)';
      badge.style.color = '#34D399';
      badge.style.border = '1px solid rgba(16,185,129,0.3)';
    } else {
      badge.textContent = 'No API Key';
      badge.style.background = 'rgba(239,68,68,0.12)';
      badge.style.color = '#F87171';
      badge.style.border = '1px solid rgba(239,68,68,0.25)';
    }
  }

  buildCharts(data);
  buildDashTable(data.recent_expenses || []);
}

function getDemoData() {
  const months = ['Oct','Nov','Dec','Jan','Feb','Mar'];
  const vals   = [9200, 12100, 11300, 14400, 16100, 18420];
  return {
    all_time_total: 81520,
    month_total:    18420,
    prev_total:     16080,
    month_count:    47,
    budget:         25000,
    groq_active:    false,
    email_active:   false,
    monthly_trend:  { labels: months, data: vals },
    category_data:  {
      'Food & Dining': 5500, 'Transportation': 3200, 'Bills & Utilities': 2800,
      'Shopping': 4100, 'Entertainment': 1600, 'Health': 900, 'Other': 320,
    },
    payment_methods: { 'UPI': 8200, 'Cash': 3500, 'Credit Card': 4800, 'Debit Card': 1920 },
    daily_data: Array.from({length:30}, (_,i) => ({ day: i+1, amount: Math.random()*1200+100 })),
    recent_expenses: [
      { id:47, date:'2026-03-18', description:'Swiggy Order',    category:'Food & Dining',  payment_method:'UPI',        amount:340  },
      { id:46, date:'2026-03-17', description:'Auto Rickshaw',   category:'Transportation', payment_method:'Cash',       amount:80   },
      { id:45, date:'2026-03-16', description:'Electricity Bill',category:'Bills & Utilities',payment_method:'Net Banking',amount:1240},
      { id:44, date:'2026-03-15', description:'Amazon Order',    category:'Shopping',       payment_method:'Credit Card',amount:2199 },
      { id:43, date:'2026-03-14', description:'Gym Membership',  category:'Health',         payment_method:'UPI',        amount:999  },
      { id:42, date:'2026-03-13', description:'Movie Tickets',   category:'Entertainment',  payment_method:'Credit Card',amount:560  },
      { id:41, date:'2026-03-12', description:'Grocery Store',   category:'Shopping',       payment_method:'Debit Card', amount:1840 },
    ],
  };
}

// ══════════════════════════════════════════════════════════
//  CHARTS
// ══════════════════════════════════════════════════════════
const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: getChartTheme().tooltipBg,
      borderColor: getChartTheme().tooltipBorder,
      borderWidth: 1,
      titleColor: getChartTheme().titleColor,
      bodyColor: getChartTheme().bodyColor,
      padding: 10,
      callbacks: {
        label: ctx => ' ₹' + ctx.raw.toLocaleString('en-IN'),
      },
    },
  },
  scales: {
    x: { grid: { color: getChartTheme().gridColor, drawBorder: false }, ticks: { color: getChartTheme().tickColor, font: { size: 11 } } },
    y: { grid: { color: getChartTheme().gridColor, drawBorder: false }, ticks: { color: getChartTheme().tickColor, font: { size: 11 }, callback: v => '₹'+v.toLocaleString('en-IN') } },
  },
};

function buildCharts(data) {
  const trend = data.monthly_trend || {};
  buildChart('chart-trend', 'bar', trend.labels || [], trend.data || [], {
    ...chartDefaults,
    showLegend: false,
    datasets_override: [{
      data: trend.data || [],
      backgroundColor: trend.data?.map((_,i) => i === (trend.data.length-1) ? '#4F6EF7' : 'rgba(79,110,247,0.35)') || [],
      borderRadius: 6, borderSkipped: false, label: 'Monthly Spend (₹)',
    }],
    plugins: {
      datalabels: null,
      tooltip: { callbacks: { label: ctx => ' ₹' + (ctx.raw||0).toLocaleString('en-IN') } }
    }
  });

  // Category donut
  const catData = data.category_data || {};
  const catLabels = Object.keys(catData);
  const catVals   = Object.values(catData);
  // Assign per-category colors
  const CAT_COLORS = {
    'Food & Dining':'#F59E0B','Transportation':'#3B82F6','Shopping':'#EC4899',
    'Entertainment':'#8B5CF6','Bills & Utilities':'#10B981','Health':'#EF4444',
    'Education':'#06B6D4','Travel':'#14B8A6','Investment':'#6366F1','Other':'#6B7280'
  };
  const catColors = catLabels.map(l => CAT_COLORS[l] || '#6B7280');
  buildDonut('chart-cat', catLabels, catVals, catColors);
  // Give category chart more height for legend
  const catCanvas = document.getElementById('chart-cat');
  if (catCanvas && catCanvas.parentElement) catCanvas.parentElement.style.minHeight = '340px';

  // Payment methods
  const pmData = data.payment_methods || {};
  buildChart('chart-pm', 'bar', Object.keys(pmData), Object.values(pmData), {
    ...chartDefaults,
    indexAxis: 'y',
    showLegend: false,
    datasets_override: [{
      data: Object.values(pmData),
      backgroundColor: C.colors.map(c => c + '55'),
      borderColor: C.colors,
      borderWidth: 1.5, borderRadius: 5,
      label: 'Amount',
    }],
  });

  // Daily line
  const daily = data.daily_data || [];
  buildChart('chart-daily', 'line', daily.map(d => d.day), daily.map(d => d.amount), {
    ...chartDefaults,
    datasets_override: [{
      data: daily.map(d => d.amount),
      borderColor: '#4F6EF7',
      backgroundColor: 'rgba(79,110,247,0.06)',
      borderWidth: 2,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
    }],
  });
}

function buildChart(id, type, labels, data, opts = {}) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (charts[id]) { charts[id].destroy(); }

  const datasets = opts.datasets_override || [{
    data,
    backgroundColor: C.colors,
    borderRadius: 5,
  }];

  const config = {
    type,
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: opts.showLegend
          ? { display: true, position: opts.legendPosition || 'bottom',
              labels: { color: getChartTheme().legendColor, usePointStyle: true, font: { size: 11 }, padding: 14 } }
          : { display: false },
        ...opts.plugins,
        tooltip: {
          backgroundColor: getChartTheme().tooltipBg, borderColor: getChartTheme().tooltipBorder, borderWidth: 1,
          titleColor: getChartTheme().titleColor, bodyColor: getChartTheme().bodyColor, padding: 10,
          callbacks: { label: ctx => ' ₹' + (ctx.raw||0).toLocaleString('en-IN') }
        }
      },
      scales: opts.scales || {},
      indexAxis: opts.indexAxis,
    },
  };

  if (opts.indexAxis) config.options.indexAxis = opts.indexAxis;
  charts[id] = new Chart(canvas, config);
}

function buildDonut(id, labels, data, colors) {
  const canvas = document.getElementById(id);
  if (!canvas) return;
  if (charts[id]) { charts[id].destroy(); }
  const bgColors = colors || C.colors;

  charts[id] = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: bgColors,
        borderWidth: 2,
        borderColor: getChartTheme().donutBorder,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: {
          display: true, position: 'bottom',
          labels: { color: getChartTheme().legendColor, usePointStyle: true, font: { size: 11 }, padding: 14,
            generateLabels: (chart) => {
              const ds = chart.data.datasets[0];
              const total = ds.data.reduce((a,b)=>a+b,0);
              return chart.data.labels.map((l,i) => ({
                text: l + '  ₹' + Math.round(ds.data[i]).toLocaleString('en-IN') + ' (' + (total ? (ds.data[i]/total*100).toFixed(1) : 0) + '%)',
                fillStyle: bgColors[i % bgColors.length],
                strokeStyle: bgColors[i % bgColors.length],
                pointStyle: 'circle', index: i,
                hidden: false,
              }));
            }
          }
        },
        tooltip: {
          backgroundColor: getChartTheme().tooltipBg, borderColor: getChartTheme().tooltipBorder, borderWidth: 1,
          titleColor: getChartTheme().titleColor, bodyColor: getChartTheme().bodyColor, padding: 10,
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a,b)=>a+b,0);
              const pct = total ? (ctx.raw/total*100).toFixed(1) : 0;
              return ' ₹' + ctx.raw.toLocaleString('en-IN') + ' (' + pct + '%)';
            }
          }
        },
      },
    },
  });

  // Build legend
  const legend = document.getElementById(id + '-legend');
  if (legend) {
    legend.innerHTML = labels.map((l, i) => {
      const pct = data[i] ? Math.round(data[i] / data.reduce((a,b)=>a+b,0) * 100) : 0;
      return `<div class="legend-item">
        <div class="legend-dot" style="background:${C.colors[i]}"></div>
        <span>${l}</span>
        <strong style="margin-left:auto;color:var(--text);">${pct}%</strong>
      </div>`;
    }).join('');
  }
}

// ══════════════════════════════════════════════════════════
//  DASHBOARD TABLE
// ══════════════════════════════════════════════════════════
let dashTableData = [];

function buildDashTable(expenses) {
  dashTableData = expenses;
  renderDashTable(expenses);
}

function filterDashTable() {
  const q = document.getElementById('dash-search').value.toLowerCase();
  const filtered = dashTableData.filter(e =>
    e.description.toLowerCase().includes(q) ||
    e.category.toLowerCase().includes(q)
  );
  renderDashTable(filtered);
}

function renderDashTable(rows) {
  const tbody = document.getElementById('dash-table-body');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="tbl-empty">No transactions found</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(e => `
    <tr>
      <td>${formatDate(e.date)}</td>
      <td style="color:var(--text);font-weight:500;">${e.description}</td>
      <td>${catBadge(e.category)}</td>
      <td>${e.payment_method || '—'}</td>
      <td style="text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--red,#EF4444);">
        ${fmtFull(e.amount)}
      </td>
    </tr>`).join('');
}

function catBadge(cat) {
  const map = {
    'Food & Dining':    'cat-food',
    'Transportation':   'cat-travel',
    'Bills & Utilities':'cat-utility',
    'Shopping':         'cat-shop',
    'Health':           'cat-health',
    'Education':        'cat-edu',
    'Investment':       'cat-invest',
  };
  const cls = map[cat] || 'cat-other';
  return `<span class="cat-badge ${cls}">${cat}</span>`;
}

function formatDate(d) {
  if (!d) return '—';
  const date = new Date(d);
  return date.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
}

// ══════════════════════════════════════════════════════════
//  EXPENSES PAGE
// ══════════════════════════════════════════════════════════
let allExpenses = [];

async function loadExpenses() {
  const data = await apiFetch('/api/expenses') || { expenses: [] };
  allExpenses = data.expenses || getDemoData().recent_expenses;

  // Populate category filter
  const cats = [...new Set(allExpenses.map(e => e.category))].sort();
  const sel  = document.getElementById('exp-cat-filter');
  sel.innerHTML = '<option value="">All Categories</option>' +
    cats.map(c => `<option value="${c}">${c}</option>`).join('');

  renderExpTable();
}

function filterExpTable() {
  appState.expFilter    = document.getElementById('exp-search').value.toLowerCase();
  appState.expCatFilter = document.getElementById('exp-cat-filter').value;
  appState.expPage      = 1;
  renderExpTable();
}

function renderExpTable() {
  const q   = appState.expFilter;
  const cat = appState.expCatFilter;
  let filtered = allExpenses.filter(e =>
    (!q   || e.description.toLowerCase().includes(q) || e.category.toLowerCase().includes(q)) &&
    (!cat || e.category === cat)
  );

  const total  = filtered.length;
  const pages  = Math.ceil(total / appState.expPageSize);
  const start  = (appState.expPage - 1) * appState.expPageSize;
  const rows   = filtered.slice(start, start + appState.expPageSize);

  const tbody = document.getElementById('exp-table-body');
  tbody.innerHTML = rows.length ? rows.map(e => `
    <tr>
      <td style="color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:0.75rem;">#${e.id}</td>
      <td>${formatDate(e.date)}</td>
      <td style="color:var(--text);font-weight:500;">${e.description}</td>
      <td>${catBadge(e.category)}</td>
      <td>${e.payment_method || '—'}</td>
      <td style="color:var(--text-muted);font-size:0.78rem;">${e.notes || ''}</td>
      <td style="text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--red,#EF4444);">
        ${fmtFull(e.amount)}
      </td>
      <td>
        <button class="row-action" onclick="deleteExpense(${e.id})" title="Delete">
          <i class="fas fa-trash-can"></i>
        </button>
      </td>
    </tr>`).join('')
  : '<tr><td colspan="8" class="tbl-empty">No expenses found</td></tr>';

  // Pagination
  const pg = document.getElementById('exp-pagination');
  if (pages <= 1) { pg.innerHTML = ''; return; }
  pg.innerHTML = [
    `<button class="pg-btn" onclick="goPage(${appState.expPage-1})" ${appState.expPage<=1?'disabled':''}>‹</button>`,
    ...Array.from({length: Math.min(pages, 7)}, (_,i) => {
      const p = i + 1;
      return `<button class="pg-btn ${p===appState.expPage?'active':''}" onclick="goPage(${p})">${p}</button>`;
    }),
    `<button class="pg-btn" onclick="goPage(${appState.expPage+1})" ${appState.expPage>=pages?'disabled':''}>›</button>`,
  ].join('');
}

function goPage(p) {
  appState.expPage = p;
  renderExpTable();
  document.getElementById('exp-table').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function expTab(t) {
  document.querySelectorAll('.page-tab').forEach((btn, i) => {
    btn.classList.toggle('active', ['view','add','import'][i] === t);
  });
  document.querySelectorAll('.exp-tab-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('exp-' + t).classList.remove('hidden');
}

async function addExpense() {
  const date   = document.getElementById('add-date').value;
  const desc   = document.getElementById('add-desc').value.trim();
  const amount = parseFloat(document.getElementById('add-amount').value);
  const cat    = document.getElementById('add-cat').value;
  const pm     = document.getElementById('add-pm').value;
  const notes  = document.getElementById('add-notes').value.trim();

  if (!desc)          return showFormAlert('add-exp-error', 'Enter a description.');
  if (isNaN(amount) || amount <= 0) return showFormAlert('add-exp-error', 'Enter a valid amount.');

  const res = await apiFetch('/api/expenses', {
    method: 'POST',
    body: JSON.stringify({ date, description: desc, amount, category: cat, payment_method: pm, notes }),
  });

  if (res?.success || res === null) {
    showFormAlert('add-exp-success', `✓ Saved: ${desc} — ${fmtFull(amount)}`);
    document.getElementById('add-desc').value   = '';
    document.getElementById('add-amount').value = '';
    document.getElementById('add-notes').value  = '';
    toast(`Expense added: ${desc}`, 'success');
    loadDashboard();
    // Check budget threshold + bill due alerts immediately
    checkEmailAlerts();
  } else {
    showFormAlert('add-exp-error', res?.message || 'Failed to save.');
  }
}

async function deleteExpense(id) {
  if (!confirm('Delete this expense?')) return;
  await apiFetch(`/api/expenses/${id}`, { method: 'DELETE' });
  allExpenses = allExpenses.filter(e => e.id !== id);
  renderExpTable();
  toast('Expense deleted', 'info');
}

function exportCSV() {
  const rows = [['ID','Date','Description','Category','Payment Method','Amount']];
  allExpenses.forEach(e => rows.push([e.id, e.date, e.description, e.category, e.payment_method, e.amount]));
  const csv = rows.map(r => r.join(',')).join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv,' + encodeURIComponent(csv);
  a.download = 'expenses.csv';
  a.click();
}

async function importFile(file) {
  if (file) previewImportFile(file);
}

// ══════════════════════════════════════════════════════════
//  BUDGET PAGE
// ══════════════════════════════════════════════════════════
async function loadBudgetPage() {
  const data = await apiFetch('/api/budget') || getDemoData();
  const spent  = data.month_total || 0;
  const budget = data.budget || 0;
  const pct    = budget ? Math.min((spent / budget) * 100, 100) : 0;

  document.getElementById('budget-meter-text').textContent  = fmt(spent);
  document.getElementById('budget-total-val').textContent   = fmt(budget);
  document.getElementById('budget-pct-label').textContent   = budget ? pct.toFixed(1) + '% of budget used' : '';
  document.getElementById('budget-bar-fill').style.width    = pct + '%';
  document.getElementById('budget-bar-fill').style.background = pct > 90 ? '#F85149' : pct > 70 ? '#D29922' : '#4F6EF7';
  if (budget) document.getElementById('set-budget-val').value = budget;

  // Forecast chart
  const forecast = data.forecast || generateForecast(data.monthly_trend);
  if (forecast) {
    const hist = data.monthly_trend || {};
    const histLabels = hist.labels || [];
    const histData   = hist.data || [];
    const foreLabels = forecast.map(f => f.month);
    const foreData   = forecast.map(f => f.predicted);

    if (charts['chart-forecast']) charts['chart-forecast'].destroy();
    charts['chart-forecast'] = new Chart(document.getElementById('chart-forecast'), {
      type: 'line',
      data: {
        labels: [...histLabels, ...foreLabels],
        datasets: [
          {
            label: 'Actual',
            data: [...histData, ...Array(foreLabels.length).fill(null)],
            borderColor: '#4F6EF7', backgroundColor: 'rgba(79,110,247,0.06)',
            borderWidth: 2, fill: true, tension: 0.4, pointRadius: 3,
          },
          {
            label: 'Forecast',
            data: [...Array(histLabels.length).fill(null), histData[histData.length-1], ...foreData],
            borderColor: '#D29922', borderDash: [5,4],
            borderWidth: 2, fill: false, tension: 0.4, pointRadius: 3,
            pointStyle: 'rectRot',
          },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, labels: { color: getChartTheme().legendColor, usePointStyle: true, font: { size: 11 } } } },
        scales: chartDefaults.scales,
      },
    });
  }

  // Recurring
  const recurring = data.recurring || [];
  const rList = document.getElementById('recurring-list');
  rList.innerHTML = recurring.length
    ? recurring.map(r => `
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);font-size:0.82rem;">
          <div>
            <div style="color:var(--text);font-weight:500;">${r.description}</div>
            <div style="color:var(--text-muted);font-size:0.72rem;">${r.occurrences} months</div>
          </div>
          <div style="color:#4F6EF7;font-family:'JetBrains Mono',monospace;">${fmt(r.avg_amount)}</div>
        </div>`).join('')
    : '<div style="color:#484F58;font-size:0.82rem;padding:20px 0;text-align:center;">No patterns yet. Add 2+ months of data.</div>';
}

function generateForecast(trend) {
  if (!trend?.data?.length) return null;
  const avg = trend.data.slice(-3).reduce((a,b)=>a+b,0) / 3;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const now = new Date();
  return [1,2,3].map(i => ({
    month: months[(now.getMonth()+i) % 12] + ' ' + (now.getFullYear() + Math.floor((now.getMonth()+i)/12)),
    predicted: Math.round(avg * (0.95 + Math.random() * 0.15)),
  }));
}

async function saveBudget() {
  const amount = parseFloat(document.getElementById('set-budget-val').value);
  if (!amount || amount <= 0) return toast('Enter a valid amount', 'error');
  const res = await apiFetch('/api/budget', {
    method: 'POST',
    body: JSON.stringify({ amount }),
  });
  toast(`Budget set to ${fmt(amount)}`, 'success');
  loadBudgetPage(); loadDashboard();
  // Immediately check if current spending already exceeds the new budget
  checkEmailAlerts();
}

// ══════════════════════════════════════════════════════════
//  BILLS
// ══════════════════════════════════════════════════════════
async function loadBills() {
  const data = await apiFetch('/api/obligations') || { obligations: [] };
  const bills = data.obligations || [];

  document.getElementById('bills-total').textContent   = bills.length;
  document.getElementById('bills-pending').textContent = bills.filter(b=>b.status==='pending').length;
  document.getElementById('bills-overdue').textContent = bills.filter(b=>b.status==='overdue').length;
  document.getElementById('bills-paid').textContent    = bills.filter(b=>b.status==='paid').length;

  const tbody = document.getElementById('bills-table-body');
  tbody.innerHTML = bills.length ? bills.map(b => `
    <tr>
      <td style="color:var(--text);font-weight:500;">${b.name}</td>
      <td style="font-family:'JetBrains Mono',monospace;">${fmt(b.amount)}</td>
      <td>${b.due_date || '—'}</td>
      <td><span class="cat-badge ${b.status==='paid'?'cat-utility':b.status==='overdue'?'cat-shop':'cat-travel'}">${b.status}</span></td>
      <td>
        ${b.status !== 'paid' ? `<button class="row-action" onclick="markBillPaid(${b.id})" title="Mark paid" style="color:#3FB950;border-color:rgba(63,185,80,0.3);">✓</button>` : ''}
        <button class="row-action" onclick="deleteBill(${b.id})" title="Delete" style="margin-left:4px;">✕</button>
      </td>
    </tr>`).join('')
  : '<tr><td colspan="5" class="tbl-empty">No bills found</td></tr>';
}

function toggleAddBill() {
  const f = document.getElementById('add-bill-form');
  f.style.display = f.style.display === 'none' ? 'grid' : 'none';
}

async function addBill() {
  const name = document.getElementById('bill-name').value.trim();
  const amt  = parseFloat(document.getElementById('bill-amt').value)||0;
  const due  = document.getElementById('bill-due').value;
  const cat  = document.getElementById('bill-cat').value;
  if (!name) return toast('Enter a bill name', 'error');
  await apiFetch('/api/obligations', {
    method: 'POST',
    body: JSON.stringify({ name, amount: amt, due_date: due, category: cat }),
  });
  toast(`Bill added: ${name}`, 'success');
  document.getElementById('bill-name').value = '';
  toggleAddBill();
  loadBills();
  // Immediately check if this bill is due tomorrow or overdue
  checkEmailAlerts();
}

async function markBillPaid(id) {
  await apiFetch(`/api/obligations/${id}/paid`, { method: 'POST' });
  toast('Bill marked as paid', 'success');
  loadBills();
}

async function deleteBill(id) {
  if (!confirm('Delete this bill?')) return;
  await apiFetch(`/api/obligations/${id}`, { method: 'DELETE' });
  loadBills();
}

// ══════════════════════════════════════════════════════════
//  AI CHAT
// ══════════════════════════════════════════════════════════
function addMessage(role, text, actions = []) {
  const area = document.getElementById('chat-area');

  // Remove welcome screen on first message
  const welcome = area.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const isUser = role === 'user';
  const initials = isUser
    ? (appState.user?.name?.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2) || 'U')
    : 'AI';

  const actionsHtml = actions.map(a =>
    `<div class="msg-action-success"><i class="fas fa-circle-check"></i> ${a}</div>`
  ).join('');

  const div = document.createElement('div');
  div.className = `msg-row ${isUser ? 'user' : ''}`;
  div.innerHTML = `
    <div class="msg-avatar ${isUser ? 'msg-avatar-user' : 'msg-avatar-ai'}">${initials}</div>
    <div>
      <div class="msg-bubble ${isUser ? 'msg-bubble-user' : 'msg-bubble-ai'}">${formatMsgText(text)}</div>
      ${actionsHtml}
    </div>`;

  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  appState.chatMessages.push({ role, content: text });
}

function formatMsgText(t) {
  return t
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code style="background:var(--surface2);padding:1px 5px;border-radius:4px;color:var(--accent);">$1</code>')
    .replace(/\n/g, '<br>');
}

function addTypingIndicator() {
  const area = document.getElementById('chat-area');
  const div  = document.createElement('div');
  div.className = 'msg-row';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="msg-avatar msg-avatar-ai">AI</div>
    <div class="msg-bubble msg-bubble-ai">
      <div class="msg-typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

async function sendMessage() {
  const input   = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('chat-send').disabled = true;

  addMessage('user', message);
  addTypingIndicator();

  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history: appState.chatMessages.slice(-12) }),
    });

    removeTypingIndicator();

    if (res) {
      addMessage('assistant', res.response || 'Sorry, no response.', res.actions || []);
      if (res.pending_expense) setPendingExpense(res.pending_expense);
      if (res.actions?.length) { loadDashboard(); loadQuickStats(); }
    } else {
      addMessage('assistant',
        "I'm having trouble connecting. Make sure your Groq API key is set in **Budget → Settings**.");
    }
  } catch (e) {
    removeTypingIndicator();
    addMessage('assistant', 'Connection error. Please try again.');
  } finally {
    document.getElementById('chat-send').disabled = false;
  }
}

function sendChip(el) {
  document.getElementById('chat-input').value = el.textContent;
  sendMessage();
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function clearChat() {
  appState.chatMessages = [];
  const area = document.getElementById('chat-area');
  area.innerHTML = `
    <div class="chat-welcome">
      <div class="chat-welcome-icon"><i class="fas fa-robot"></i></div>
      <div class="chat-welcome-title">SmartFinance AI</div>
      <div class="chat-welcome-sub">Chat cleared. Ask me anything!</div>
    </div>`;
}

function setPendingExpense(exp) {
  appState.pendingExpense = exp;
  const card = document.getElementById('pending-expense-card');
  const det  = document.getElementById('pending-expense-details');
  det.innerHTML = `
    <div style="font-size:0.82rem;color:#9BA3B4;margin:8px 0;">
      <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);">
        <span>Description</span><strong style="color:var(--text);">${exp.vendor||'Unknown'}</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);">
        <span>Amount</span><strong style="color:#4F6EF7;">${fmtFull(exp.total||0)}</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:4px 0;">
        <span>Category</span><span>${catBadge(exp.category||'Other')}</span>
      </div>
    </div>`;
  card.style.display = 'block';
}

async function confirmExpense() {
  const e = appState.pendingExpense;
  if (!e) return;
  await apiFetch('/api/expenses', {
    method: 'POST',
    body: JSON.stringify({
      date: e.date || new Date().toISOString().split('T')[0],
      description: e.vendor || 'Unknown',
      amount: e.total || 0,
      category: e.category || 'Other',
      payment_method: 'Not Specified',
    }),
  });
  addMessage('assistant', `✓ Expense saved: **${e.vendor}** — ${fmtFull(e.total)}`);
  document.getElementById('pending-expense-card').style.display = 'none';
  appState.pendingExpense = null;
  toast('Expense saved', 'success');
  loadDashboard();
}

function skipExpense() {
  document.getElementById('pending-expense-card').style.display = 'none';
  appState.pendingExpense = null;
}

// File upload drag-drop
function setupDragDrop() {
  const drop = document.getElementById('upload-drop');
  if (!drop) return;
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag-over'); });
  drop.addEventListener('dragleave',  () => drop.classList.remove('drag-over'));
  drop.addEventListener('drop', e => {
    e.preventDefault(); drop.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  });
  drop.addEventListener('click', () => document.getElementById('file-input').click());
}

async function handleFileUpload(file) {
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  addMessage('user', `📎 Uploaded: **${file.name}**`);
  addTypingIndicator();

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res  = await fetch(API_BASE + '/api/upload', { method:'POST', body:fd });
    const data = res.ok ? await res.json() : null;
    removeTypingIndicator();

    if (!data) {
      addMessage('assistant', 'Server error. Make sure server.py is running.');
      return;
    }

    // ── Dataset (Excel / CSV / TXT) — show confirmation, do NOT auto-import ──
    if (data.is_dataset) {
      // Store pending dataset for user to confirm
      appState.pendingDataset = { file, filename: file.name, summary: data.summary, preview: data.preview, rowCount: data.row_count };

      const previewText = data.preview
        ? data.preview.split('\n').slice(0,6).join('\n')
        : 'Preview not available';

      addMessage('assistant',
        `📊 **${file.name}** analysed!\n\n` +
        `I found expense data in this file.\n\n` +
        `**Summary:** ${data.summary}\n\n` +
        `Check the panel on the right to confirm whether to add these expenses.`
      );

      // Show confirmation card in tools panel
      showDatasetConfirmCard(file.name, previewText, data.summary);

    // ── Document (PDF / Image / DOCX) ─────────────────────────────────────
    } else {
      const summary = data.summary || `Processed ${file.name}`;
      let reply = `✅ **${file.name}** analysed!\n\n${summary}`;
      if (data.financial?.total) {
        reply += `\n\n💰 **Detected:** ₹${parseFloat(data.financial.total).toLocaleString('en-IN',{minimumFractionDigits:2})} — ${data.financial.category||'Other'}`;
        setPendingExpense(data.financial);
      } else {
        reply += '\n\nNo financial amount detected. You can ask me to add an expense manually.';
      }
      addMessage('assistant', reply);
    }

  } catch (e) {
    removeTypingIndicator();
    addMessage('assistant', `Error: ${e.message}. Make sure server.py is running.`);
  }
}

function showDatasetConfirmCard(filename, preview, summary) {
  const card = document.getElementById('dataset-confirm-card');
  if (!card) return;

  document.getElementById('dataset-confirm-filename').textContent = filename;
  document.getElementById('dataset-preview-content').textContent  = preview || 'No preview available';
  document.getElementById('dataset-confirm-summary').textContent  = summary || '';
  card.style.display = 'block';
}

async function confirmDatasetImport() {
  const ds = appState.pendingDataset;
  if (!ds) return;

  const card = document.getElementById('dataset-confirm-card');
  if (card) card.style.display = 'none';

  addMessage('user', 'Yes, add all expenses to my account.');
  addTypingIndicator();

  const fd = new FormData();
  fd.append('file', ds.file);

  try {
    const res  = await fetch(API_BASE + '/api/import', { method:'POST', body:fd });
    const data = res.ok ? await res.json() : null;
    removeTypingIndicator();

    if (data?.success) {
      addMessage('assistant',
        `✅ **Done!** ${data.message}\n\nAll expenses from **${ds.filename}** have been added to your account.\n\nGo to the **Expenses** page to view them.`,
        []
      );
      toast(data.message, 'success');
      loadQuickStats();
      checkEmailAlerts();
    } else {
      addMessage('assistant', `❌ Import failed: ${data?.message || 'Unknown error'}`);
    }
  } catch (e) {
    removeTypingIndicator();
    addMessage('assistant', `Import error: ${e.message}`);
  }

  appState.pendingDataset = null;
}

function cancelDatasetImport() {
  const card = document.getElementById('dataset-confirm-card');
  if (card) card.style.display = 'none';
  appState.pendingDataset = null;
  addMessage('assistant', 'No problem — the file was not imported. You can upload a different file or add expenses manually.');
}

function toggleCamera() {
  const btn = document.getElementById('cam-btn');
  const area = document.getElementById('cam-area');
  if (area.style.display === 'none') {
    area.style.display = 'block';
    area.innerHTML = `<video id="cam-video" style="width:100%;border-radius:8px;" autoplay></video>
      <button class="tool-btn" style="margin-top:8px;" onclick="capturePhoto()"><i class="fas fa-camera"></i> Capture</button>`;
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(s => { document.getElementById('cam-video').srcObject = s; })
      .catch(() => { area.innerHTML = '<p style="color:#F85149;font-size:0.8rem;">Camera access denied.</p>'; });
    btn.innerHTML = '<i class="fas fa-xmark"></i> Close Camera';
  } else {
    const v = document.getElementById('cam-video');
    if (v?.srcObject) v.srcObject.getTracks().forEach(t=>t.stop());
    area.style.display = 'none';
    area.innerHTML = '';
    btn.innerHTML = '<i class="fas fa-camera"></i> Open Camera';
  }
}

async function capturePhoto() {
  const video = document.getElementById('cam-video');
  if (!video) return;
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(async blob => {
    const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
    toggleCamera();
    await handleFileUpload(file);
  }, 'image/jpeg');
}

async function loadQuickStats() {
  const data = await apiFetch('/api/dashboard');
  if (!data) {
    console.warn('Could not load dashboard data from server. Is server.py running?');
    return;
  }
  document.getElementById('qs-alltime').textContent = fmt(data.all_time_total);
  document.getElementById('qs-month').textContent   = fmt(data.month_total);
  document.getElementById('qs-entries').textContent = data.total_count || allExpenses.length;
}


// ══════════════════════════════════════════════════════════
//  SETTINGS FUNCTIONS
// ══════════════════════════════════════════════════════════
async function saveGroqKey() {
  const key = (document.getElementById('groq-key')?.value || '').trim();
  if (!key) return toast('Enter a Groq API key', 'error');
  await apiFetch('/api/settings/groq', { method:'POST', body:JSON.stringify({key}) });
  const el = document.getElementById('groq-result');
  if (el) { el.textContent='✓ Key saved. Click Test to verify.'; el.style.color='#3FB950'; }
  toast('Groq API key saved!', 'success');
  // Immediately test and update badge
  await testGroqAndUpdateBadge(key);
}

async function testGroqAndUpdateBadge(key) {
  const badge = document.getElementById('chat-ai-badge');
  if (badge) { badge.textContent = 'Testing...'; badge.style.background='rgba(245,158,11,0.12)'; badge.style.color='#FCD34D'; badge.style.border='1px solid rgba(245,158,11,0.3)'; }
  const res = await apiFetch('/api/settings/groq/test', { method:'POST', body:JSON.stringify({key: key || (document.getElementById('groq-key')?.value||'').trim()}) });
  if (badge) {
    if (res?.success) {
      badge.textContent = 'Connected'; badge.style.background='rgba(16,185,129,0.15)';
      badge.style.color='#34D399'; badge.style.border='1px solid rgba(16,185,129,0.3)';
      document.getElementById('sb-ai-status').innerHTML='<span class="status-dot dot-green"></span><span style="color:#3FB950;">AI: Active</span>';
    } else {
      badge.textContent = 'Key Error'; badge.style.background='rgba(239,68,68,0.12)';
      badge.style.color='#F87171'; badge.style.border='1px solid rgba(239,68,68,0.25)';
    }
  }
}

async function testGroq() {
  const key = (document.getElementById('groq-key')?.value || '').trim();
  const res = await apiFetch('/api/settings/groq/test', { method:'POST', body:JSON.stringify({key}) });
  const el  = document.getElementById('groq-result');
  if (!el) return;
  if (res?.success) { el.textContent='✓ '+(res.message||'Groq connected!'); el.style.color='#3FB950'; }
  else              { el.textContent='✗ '+(res?.message||'Connection failed.'); el.style.color='#F85149'; }
  await testGroqAndUpdateBadge(key);
}

async function saveEmailSettings() {
  const email = (document.getElementById('sender-email')?.value||'').trim();
  const pass  = (document.getElementById('sender-pass')?.value||'').trim();
  if (!email || !pass) return toast('Enter Gmail and App Password', 'error');
  await apiFetch('/api/settings/email', { method:'POST', body:JSON.stringify({email,password:pass}) });
  const el = document.getElementById('email-result');
  if (el) { el.textContent='✓ Settings saved.'; el.style.color='#3FB950'; }
  toast('Email settings saved!', 'success');
}

async function testEmail() {
  const email = (document.getElementById('sender-email')?.value||'').trim();
  const pass  = (document.getElementById('sender-pass')?.value||'').trim();
  const res   = await apiFetch('/api/settings/email/test', { method:'POST', body:JSON.stringify({email,password:pass}) });
  const el    = document.getElementById('email-result');
  if (!el) return;
  el.textContent = res?.success ? '✓ '+(res.message||'Connected!') : '✗ '+(res?.message||'Failed.');
  el.style.color = res?.success ? '#3FB950' : '#F85149';
}

async function sendTestEmail() {
  const res = await apiFetch('/api/settings/email/send-test', { method:'POST' });
  const el  = document.getElementById('email-result');
  if (!el) return;
  el.textContent = res?.success ? '✓ Test email sent!' : '✗ '+(res?.message||'Failed. Check settings.');
  el.style.color = res?.success ? '#3FB950' : '#F85149';
}

// Threshold checkboxes
let selectedThresholds = [80, 100];

function renderThresholdCheckboxes(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const allLevels = [50, 60, 70, 80, 90, 100];
  container.innerHTML = allLevels.map(lvl => `
    <label style="display:flex;align-items:center;gap:5px;font-size:0.8rem;color:#9BA3B4;cursor:pointer;
      background:var(--surface2);border:1px solid ${selectedThresholds.includes(lvl)?'#4F6EF7':'var(--border)'};
      border-radius:6px;padding:5px 10px;transition:all 0.15s;">
      <input type="checkbox" value="${lvl}" style="accent-color:#4F6EF7;"
        ${selectedThresholds.includes(lvl)?'checked':''}
        onchange="toggleThreshold(${lvl},this.checked,'${containerId}')">
      ${lvl}%
    </label>`).join('');
}

function toggleThreshold(lvl, checked, containerId) {
  if (checked && !selectedThresholds.includes(lvl)) selectedThresholds.push(lvl);
  if (!checked) selectedThresholds = selectedThresholds.filter(t => t !== lvl);
  selectedThresholds.sort((a,b)=>a-b);
  renderThresholdCheckboxes(containerId);
  const other = containerId === 'threshold-checkboxes' ? 'threshold-checkboxes-email' : 'threshold-checkboxes';
  renderThresholdCheckboxes(other);
}

async function saveThresholds() {
  const val = selectedThresholds.join(',');
  await apiFetch('/api/account/update', { method:'POST', body:JSON.stringify({thresholds:val}) });
  toast('Thresholds saved', 'success');
}

async function saveAlertSettings() {
  const emailEnabled = document.getElementById('email-enabled-toggle')?.checked ? 1 : 0;
  await apiFetch('/api/account/update', {
    method:'POST', body:JSON.stringify({ email_enabled:emailEnabled, thresholds:selectedThresholds.join(',') }),
  });
  const el = document.getElementById('alert-settings-result');
  if (el) { el.textContent='✓ Alert settings saved!'; el.style.color='#3FB950'; }
  toast('Alert settings saved!', 'success');
}

async function loadAccountInfo() {
  const data = await apiFetch('/api/account/info');
  if (!data) return;
  const set = (id, val) => { const el=document.getElementById(id); if(el) el.value=val||''; };
  set('acc-name', data.name); set('acc-email', data.email);
  set('acc-phone', data.phone); set('acc-budget-alert', data.budget_alert||80);
  const toggle = document.getElementById('email-enabled-toggle');
  if (toggle) toggle.checked = !!data.email_enabled;
  if (data.thresholds) {
    try { selectedThresholds = data.thresholds.split(',').map(Number).filter(Boolean); } catch(e) {}
  }
  renderThresholdCheckboxes('threshold-checkboxes');
  renderThresholdCheckboxes('threshold-checkboxes-email');
  if (data.groq_configured) {
    const el = document.getElementById('groq-result');
    if (el) { el.textContent='✓ Groq key is configured.'; el.style.color='#3FB950'; }
  }
}

function loadSettingsEmailFields() { loadAccountInfo(); }

async function updateAccount() {
  const name  = (document.getElementById('acc-name')?.value||'').trim();
  const email = (document.getElementById('acc-email')?.value||'').trim();
  const alert = parseInt(document.getElementById('acc-budget-alert')?.value||80);
  const emailEnabled = document.getElementById('email-enabled-toggle')?.checked ? 1 : 0;
  const res = await apiFetch('/api/account/update', {
    method:'POST', body:JSON.stringify({ name, email, budget_alert:alert, email_enabled:emailEnabled }),
  });
  const el = document.getElementById('acc-update-result');
  if (res?.success) {
    if (el) { el.textContent='✓ Account updated!'; el.style.color='#3FB950'; }
    localStorage.setItem('sfb_user', JSON.stringify({...appState.user, name, email}));
    appState.user = {...appState.user, name, email};
    setUserUI(); toast('Account updated!', 'success');
  } else {
    if (el) { el.textContent='✗ '+(res?.message||'Failed.'); el.style.color='#F85149'; }
  }
}

async function changePin() {
  const oldPin = (document.getElementById('old-pin')?.value||'').trim();
  const newPin = (document.getElementById('new-pin')?.value||'').trim();
  const newPin2= (document.getElementById('new-pin2')?.value||'').trim();
  const el     = document.getElementById('pin-change-result');
  if (newPin !== newPin2) { if(el){el.textContent='✗ PINs do not match.';el.style.color='#F85149';} return; }
  if (newPin.length!==4 || !/^\d+$/.test(newPin)) { if(el){el.textContent='✗ PIN must be 4 digits.';el.style.color='#F85149';} return; }
  const res = await apiFetch('/api/account/change-pin', {
    method:'POST', body:JSON.stringify({ old_pin:oldPin, new_pin:newPin }),
  });
  if (res?.success) {
    if (el) { el.textContent='✓ PIN changed!'; el.style.color='#3FB950'; }
    ['old-pin','new-pin','new-pin2'].forEach(id => { const e=document.getElementById(id); if(e) e.value=''; });
    toast('PIN changed!', 'success');
  } else { if(el){el.textContent='✗ '+(res?.message||'Failed.');el.style.color='#F85149';} }
}

async function checkEmailAlerts() {
  try {
    const res = await apiFetch('/api/alerts/check', { method: 'POST' });
    if (!res) return;

    // Show success toast for each email that was actually sent
    if (res.sent?.length) {
      res.sent.forEach(msg => toast('📧 ' + msg, 'success'));
    }

    // Show error toasts so user knows email failed and why
    if (res.errors?.length) {
      res.errors.forEach(errMsg => {
        console.warn('[Email Alert]', errMsg);
        toast('⚠ Alert email failed: ' + errMsg, 'error');
      });
    }
  } catch (e) {
    console.warn('[checkEmailAlerts] network error:', e.message);
  }
}

function confirmDelete() { document.getElementById('delete-modal').style.display='flex'; }
function closeDeleteModal() { document.getElementById('delete-modal').style.display='none'; }

async function deleteAccount() {
  const pin = (document.getElementById('delete-pin')?.value||'').trim();
  if (pin.length!==4) return toast('Enter your 4-digit PIN','error');
  const res = await apiFetch('/api/account', { method:'DELETE', body:JSON.stringify({pin}) });
  if (res?.success) { localStorage.clear(); window.location.href='login.html'; }
  else toast(res?.message||'Wrong PIN','error');
}

// ══════════════════════════════════════════════════════════
//  FORECAST TAB
// ══════════════════════════════════════════════════════════
async function loadForecastTab() {
  const data = await apiFetch('/api/budget');
  if (!data) return;
  const hist=data.monthly_trend||{}, fore=data.forecast||[];
  const hL=hist.labels||[], hD=hist.data||[];
  const fL=fore.map(f=>f.month), fD=fore.map(f=>Math.round(f.predicted));

  if (charts['chart-forecast']) charts['chart-forecast'].destroy();
  const fcCanvas = document.getElementById('chart-forecast');
  if (fcCanvas) {
    charts['chart-forecast'] = new Chart(fcCanvas, {
      type:'line',
      data:{ labels:[...hL,...fL], datasets:[
        { label:'Actual', data:[...hD,...Array(fL.length).fill(null)],
          borderColor:'#4F6EF7', backgroundColor:'rgba(79,110,247,0.07)',
          borderWidth:2.5, fill:true, tension:0.4, pointRadius:4 },
        { label:'Forecast', data:[...Array(hL.length).fill(null),hD[hD.length-1]||0,...fD],
          borderColor:'#D29922', borderDash:[5,4], borderWidth:2, fill:false, tension:0.4,
          pointStyle:'rectRot', pointRadius:5 },
      ]},
      options:{ responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{ display:true, labels:{color:getChartTheme().legendColor,usePointStyle:true,font:{size:11}} } },
        scales:chartDefaults.scales },
    });
  }

  const fc = document.getElementById('forecast-cards');
  if (fc) {
    fc.innerHTML = fore.map(f=>`
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:16px;text-align:center;">
        <div style="font-size:0.72rem;color:#4B5262;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px;">${f.month}</div>
        <div style="font-size:1.4rem;font-weight:700;color:var(--text);font-family:'JetBrains Mono',monospace;">
          ₹${Math.round(f.predicted).toLocaleString('en-IN')}</div>
        <div style="font-size:0.72rem;color:#4B5262;margin-top:4px;">predicted</div>
      </div>`).join('');
  }

  const wd = await apiFetch('/api/weekday');
  const wdCanvas = document.getElementById('chart-weekday');
  if (wd?.totals && wdCanvas) {
    const days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const vals=days.map(d=>Math.round(wd.totals[d]||0));
    if (charts['chart-weekday']) charts['chart-weekday'].destroy();
    charts['chart-weekday'] = new Chart(wdCanvas, {
      type:'bar',
      data:{ labels:days, datasets:[{ data:vals,
        backgroundColor:vals.map(v=>v===Math.max(...vals)?'#4F6EF7':'rgba(79,110,247,0.3)'),
        borderRadius:6, borderSkipped:false }] },
      options:{ responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:false}}, scales:chartDefaults.scales },
    });
  }
}

// ══════════════════════════════════════════════════════════
//  RECURRING TAB
// ══════════════════════════════════════════════════════════
async function loadRecurringTab() {
  const data = await apiFetch('/api/recurring');
  if (!data) return;
  const pList = document.getElementById('recurring-patterns-list');
  if (pList) {
    const patterns = data.patterns||[];
    pList.innerHTML = patterns.length ? patterns.map(p=>`
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-size:0.87rem;font-weight:600;color:var(--text);text-transform:capitalize;">${p.description}</div>
          <div style="font-size:0.74rem;color:#4B5262;margin-top:2px;">${p.occurrences} months &nbsp;·&nbsp; avg ₹${Math.round(p.avg_amount).toLocaleString('en-IN')}</div>
        </div>
        <button class="tbl-btn" onclick="markAllRecurring('${p.description.replace(/'/g,"\\'")}')">Mark Recurring</button>
      </div>`).join('')
    : '<div class="tbl-empty" style="padding:24px;">No patterns detected. Add expenses across 2+ months.</div>';
  }
  const mBody = document.getElementById('marked-recurring-body');
  if (mBody) {
    const marked = data.marked||[];
    mBody.innerHTML = marked.length ? marked.slice(0,20).map(e=>`
      <tr>
        <td>${formatDate(e.date)}</td>
        <td style="color:var(--text);font-weight:500;">${e.description}</td>
        <td>${catBadge(e.category)}</td>
        <td style="text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--red,#EF4444);">
          ₹${parseFloat(e.amount).toLocaleString('en-IN',{minimumFractionDigits:2})}</td>
      </tr>`).join('')
    : '<tr><td colspan="4" class="tbl-empty">No marked expenses</td></tr>';
  }
}

async function markAllRecurring(desc) {
  const expenses = allExpenses.filter(e=>e.description.toLowerCase()===desc.toLowerCase());
  await Promise.all(expenses.map(e=>apiFetch(`/api/recurring/${e.id}/mark`,{method:'POST'})));
  toast(`Marked "${desc}" as recurring`,'success');
  loadRecurringTab(); loadExpenses();
}

// ══════════════════════════════════════════════════════════
//  SCENARIO SIMULATION
// ══════════════════════════════════════════════════════════
async function loadScenarioCategories() {
  const data = await apiFetch('/api/scenario/categories');
  const sel  = document.getElementById('sim-category');
  if (!sel||!data?.categories?.length) return;
  const totals = data.totals||{};
  sel.innerHTML = '<option value="">Select category...</option>' +
    data.categories.map(c=>`<option value="${c}">${c} — ₹${Math.round(totals[c]||0).toLocaleString('en-IN')}</option>`).join('');
}

async function runSimulation() {
  const cat = document.getElementById('sim-category')?.value;
  const pct = parseInt(document.getElementById('sim-slider')?.value||20);
  if (!cat) return toast('Select a category first','error');
  const res = await apiFetch('/api/scenario',{method:'POST',body:JSON.stringify({category:cat,increase_pct:pct})});
  if (!res?.result) return toast('No data for this category','error');
  const r = res.result;
  const wrap = document.getElementById('sim-result');
  if (wrap) wrap.style.display='block';
  const nums = document.getElementById('sim-numbers');
  if (nums) {
    const diff = r.new_total - r.current_total;
    nums.innerHTML = [
      ['Current '+cat, Math.round(r.current_amount), 'var(--text)', 'var(--surface2)', 'var(--border)'],
      ['After +'+pct+'%', Math.round(r.increased_amount), '#D29922', 'var(--surface2)', 'var(--border)'],
      ['Current Total', Math.round(r.current_total), 'var(--text)', 'var(--surface2)', 'var(--border)'],
      ['New Total (+₹'+Math.round(diff).toLocaleString('en-IN')+')', Math.round(r.new_total), '#F85149', 'rgba(248,81,73,0.08)', 'rgba(248,81,73,0.2)'],
    ].map(([label,val,color,bg,border])=>`
      <div style="background:${bg};border:1px solid ${border};border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:0.68rem;color:#4B5262;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">${label}</div>
        <div style="font-size:1.3rem;font-weight:700;color:${color};font-family:'JetBrains Mono',monospace;">₹${val.toLocaleString('en-IN')}</div>
      </div>`).join('');
  }
  const simCanvas = document.getElementById('chart-sim');
  if (simCanvas) {
    if (charts['chart-sim']) charts['chart-sim'].destroy();
    const allCats = Object.keys(r.all_categories||{});
    charts['chart-sim'] = new Chart(simCanvas, {
      type:'bar',
      data:{ labels:allCats, datasets:[
        { label:'Current', data:allCats.map(c=>Math.round(r.all_categories[c])),
          backgroundColor:'rgba(79,110,247,0.5)', borderRadius:5 },
        { label:'Simulated', data:allCats.map(c=>c===cat?Math.round(r.increased_amount):Math.round(r.all_categories[c])),
          backgroundColor:allCats.map(c=>c===cat?'rgba(248,81,73,0.7)':'rgba(79,110,247,0.2)'), borderRadius:5 },
      ]},
      options:{ responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:true,labels:{color:getChartTheme().legendColor,font:{size:11}}}},
        scales:{...getChartDefaults().scales, x:{...getChartDefaults().scales.x,ticks:{color:getChartTheme().tickColor,font:{size:10},maxRotation:35}}} },
    });
  }
}

// ══════════════════════════════════════════════════════════
//  BUDGET OVERVIEW (loadBudgetPage replaces old version)
// ══════════════════════════════════════════════════════════
async function loadBudgetPage() {
  const data = await apiFetch('/api/budget');
  if (!data) return;
  const spent=data.month_total||0, budget=data.budget||0;
  const pct = budget ? Math.min((spent/budget)*100,100) : 0;
  const mText=document.getElementById('budget-meter-text'); if(mText) mText.textContent=fmt(spent);
  const bVal=document.getElementById('budget-total-val');   if(bVal) bVal.textContent=fmt(budget);
  const bFill=document.getElementById('budget-bar-fill');
  if (bFill) { bFill.style.width=pct+'%'; bFill.style.background=pct>90?'#F85149':pct>70?'#D29922':'#4F6EF7'; }
  const pLabel=document.getElementById('budget-pct-label');
  if (pLabel) pLabel.textContent = budget ? pct.toFixed(1)+'% of budget used' : '';
  const bInput=document.getElementById('set-budget-val'); if(bInput&&budget) bInput.value=budget;

  const catData = await apiFetch('/api/dashboard');
  if (catData?.category_data && document.getElementById('chart-budget-cat')) {
    buildDonut('chart-budget-cat', Object.keys(catData.category_data), Object.values(catData.category_data));
  }
  const info = await apiFetch('/api/account/info');
  if (info?.thresholds) {
    try { selectedThresholds=info.thresholds.split(',').map(Number).filter(Boolean); } catch(e) {}
  }
  renderThresholdCheckboxes('threshold-checkboxes');
}

// Budget tab switcher
function budgetTab(t) {
  const tabs=['overview','bills','forecast','recurring','scenario'];
  document.querySelectorAll('#page-budget .page-tab').forEach((b,i)=>b.classList.toggle('active',tabs[i]===t));
  tabs.forEach(id=>{ const el=document.getElementById('btab-'+id); if(el) el.classList.toggle('hidden',id!==t); });
  if (t==='forecast')  loadForecastTab();
  if (t==='recurring') loadRecurringTab();
  if (t==='scenario')  loadScenarioCategories();
}

function settingsTab(t) {
  const tabs=['ai','email','account','danger'];
  document.querySelectorAll('#page-settings .page-tab').forEach((b,i)=>b.classList.toggle('active',tabs[i]===t));
  tabs.forEach(id=>{ const el=document.getElementById('stab-'+id); if(el) el.classList.toggle('hidden',id!==t); });
  if (t==='email') renderThresholdCheckboxes('threshold-checkboxes-email');
}

// ══════════════════════════════════════════════════════════
//  MISC
// ══════════════════════════════════════════════════════════
async function logout() {
  try { await fetch('/api/logout',{method:'POST'}); } catch(e) {}
  localStorage.clear(); window.location.href='login.html';
}

function refreshData() {
  const page=document.querySelector('.sb-nav-item.active')?.dataset.page||'dashboard';
  navigate(page); toast('Refreshed','info');
}

function showFormAlert(id,msg) {
  const el=document.getElementById(id); if(!el) return;
  el.innerHTML=`<i class="fas fa-circle-exclamation"></i> ${msg}`;
  el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),4000);
}

function toast(msg, type='info') {
  const wrap=document.getElementById('toast-wrap'); if(!wrap) return;
  const div=document.createElement('div'); div.className=`toast ${type}`;
  const icons={success:'fas fa-circle-check',error:'fas fa-circle-xmark',info:'fas fa-circle-info'};
  div.innerHTML=`<i class="${icons[type]||icons.info}" style="color:${type==='success'?'#3FB950':type==='error'?'#F85149':'#4F6EF7'};"></i> ${msg}`;
  wrap.appendChild(div); setTimeout(()=>div.remove(),3500);
}

// ══════════════════════════════════════════════════════════
//  THEME TOGGLE — light / dark
// ══════════════════════════════════════════════════════════
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('sfb_theme', newTheme);
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
  }
  // Re-render charts with new theme colors
  if (appState.allDashData) buildCharts(appState.allDashData);
}

function initTheme() {
  const saved = localStorage.getItem('sfb_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  const icon = document.getElementById('theme-icon');
  if (icon) icon.className = saved === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// ══════════════════════════════════════════════════════════
//  ROBUST CAMERA — live image processing
// ══════════════════════════════════════════════════════════
let camStream = null;

function toggleCamera() {
  const area    = document.getElementById('cam-area');
  const togBtn  = document.getElementById('cam-toggle-btn');

  if (area.style.display === 'none' || area.style.display === '') {
    // Open camera
    area.style.display = 'block';
    area.innerHTML = `
      <div style="position:relative;border-radius:12px;overflow:hidden;background:#000;">
        <video id="cam-video" style="width:100%;display:block;max-height:260px;object-fit:cover;" autoplay playsinline></video>
        <div style="position:absolute;top:8px;right:8px;display:flex;gap:6px;">
          <button onclick="capturePhoto()" style="background:var(--accent);border:none;border-radius:8px;color:white;padding:7px 14px;font-size:0.82rem;font-weight:700;cursor:pointer;font-family:Inter,sans-serif;">
            <i class="fas fa-camera"></i> Capture
          </button>
          <button onclick="toggleCamera()" style="background:rgba(239,68,68,0.8);border:none;border-radius:8px;color:white;padding:7px 12px;font-size:0.82rem;cursor:pointer;">
            <i class="fas fa-xmark"></i>
          </button>
        </div>
        <div id="cam-flash" style="position:absolute;inset:0;background:white;opacity:0;pointer-events:none;transition:opacity 0.1s;border-radius:12px;"></div>
      </div>`;

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
    })
    .then(stream => {
      camStream = stream;
      const video = document.getElementById('cam-video');
      if (video) { video.srcObject = stream; video.play(); }
      if (togBtn) { togBtn.querySelector('i').className = 'fas fa-video-slash'; togBtn.title = 'Close Camera'; }
    })
    .catch(err => {
      console.error('Camera error:', err);
      area.innerHTML = `
        <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;padding:16px;font-size:0.83rem;color:#F87171;text-align:center;">
          <i class="fas fa-camera-slash" style="font-size:1.4rem;margin-bottom:8px;display:block;"></i>
          Camera access denied.<br>
          <span style="font-size:0.76rem;color:var(--text-dim);">Allow camera in browser settings, or upload an image file instead.</span>
        </div>`;
    });
  } else {
    // Close camera
    if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
    area.style.display = 'none';
    area.innerHTML = '';
    if (togBtn) { togBtn.querySelector('i').className = 'fas fa-camera'; togBtn.title = 'Camera'; }
  }
}

async function capturePhoto() {
  const video = document.getElementById('cam-video');
  if (!video || !video.videoWidth) { toast('Camera not ready yet', 'error'); return; }

  const flash = document.getElementById('cam-flash');
  if (flash) { flash.style.opacity = '0.7'; setTimeout(() => flash.style.opacity = '0', 200); }

  const canvas = document.createElement('canvas');
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  // Image enhancement for better OCR: increase contrast + sharpen
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = imageData.data;
  // Simple contrast boost
  const factor = 1.3;
  for (let i = 0; i < d.length; i += 4) {
    d[i]   = Math.min(255, Math.max(0, factor * (d[i]   - 128) + 128));
    d[i+1] = Math.min(255, Math.max(0, factor * (d[i+1] - 128) + 128));
    d[i+2] = Math.min(255, Math.max(0, factor * (d[i+2] - 128) + 128));
  }
  ctx.putImageData(imageData, 0, 0);

  canvas.toBlob(async blob => {
    const file = new File([blob], `bill_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
    toast('📸 Photo captured! Analysing with AI...', 'info');
    toggleCamera();
    // Show processing indicator in chat
    addTypingIndicator();
    addMessage('user', '📷 **Camera capture** — analysing bill/receipt...');
    removeTypingIndicator();
    await handleCameraUpload(file);
  }, 'image/jpeg', 0.95);
}

// Dedicated camera upload handler — smarter than generic handleFileUpload
async function handleCameraUpload(file) {
  addTypingIndicator();
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res  = await fetch(API_BASE + '/api/upload', { method: 'POST', body: fd });
    const data = res.ok ? await res.json() : null;
    removeTypingIndicator();

    if (!data) {
      addMessage('assistant', '❌ Server error processing image. Make sure server.py is running.');
      return;
    }

    const fin = data.financial || {};
    let reply  = `✅ **Image processed!**\n\n`;

    // Summary
    if (data.summary) reply += `📄 **Summary:** ${data.summary}\n\n`;

    // Financial extraction results
    if (fin.total && fin.total > 0) {
      reply += `💰 **Amount detected:** ₹${parseFloat(fin.total).toLocaleString('en-IN', {minimumFractionDigits:2})}\n`;
      if (fin.vendor)   reply += `🏢 **Vendor/Payee:** ${fin.vendor}\n`;
      if (fin.date)     reply += `📅 **Date:** ${fin.date}\n`;
      if (fin.category) reply += `🏷 **Category:** ${fin.category}\n`;
      if (fin.invoice_no) reply += `🧾 **Invoice No:** ${fin.invoice_no}\n`;
      if (fin.gst_no)   reply += `📋 **GST No:** ${fin.gst_no}\n`;
      if (fin.due_date) reply += `⏰ **Due Date:** ${fin.due_date}\n`;

      reply += `\n**What would you like to do?**`;
      setPendingExpense(fin);
    } else if (data.doc_type === 'bill' || data.doc_type === 'invoice' || data.doc_type === 'utility_bill') {
      reply += `📄 **Document type:** ${data.doc_type}\n`;
      reply += `No amount was extracted automatically. You can:\n`;
      reply += `• Say: *"Add bill ₹1200 due on 25th"*\n`;
      reply += `• Or add manually in the **Bills** section.`;
    } else {
      reply += `No financial amount detected. You can add an expense manually or ask me to do it.`;
    }

    // Auto-create bill obligation if it looks like a bill/invoice with due date
    if (fin.due_date && fin.total && (data.doc_type === 'utility_bill' || data.doc_type === 'invoice' || data.doc_type === 'bill')) {
      try {
        await apiFetch('/api/obligations', {
          method: 'POST',
          body: JSON.stringify({
            name: fin.vendor || data.doc_type || 'Bill from scan',
            amount: fin.total || 0,
            due_date: fin.due_date,
            category: fin.category || 'Bills & Utilities',
          }),
        });
        reply += `\n\n✅ **Bill automatically added** to your Bills tracker with due date ${fin.due_date}!`;
        loadBills();
        checkEmailAlerts();
      } catch(e) {}
    }

    addMessage('assistant', reply, data.actions || []);
  } catch(e) {
    removeTypingIndicator();
    addMessage('assistant', `❌ Camera processing error: ${e.message}`);
  }
}

// ══════════════════════════════════════════════════════════
//  REPORT PAGE
// ══════════════════════════════════════════════════════════
let reportData = null;
let reportExpenses = [];

async function loadReport() {
  const monthSel = document.getElementById('report-month-filter');

  // Build dropdown once (first visit)
  if (monthSel && monthSel.options.length <= 1) {
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const d   = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const val = d.toISOString().slice(0, 7);
      const lbl = d.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
      const opt = new Option(lbl, val);
      if (i === 0) opt.selected = true;
      monthSel.add(opt);
    }
  }

  // Always read the currently-selected month (default = current month)
  const selectedMonth = monthSel?.value || new Date().toISOString().slice(0, 7);

  // Fetch only what we need
  const [allExpRes, budgetRes, oblRes] = await Promise.all([
    apiFetch('/api/expenses'),
    apiFetch('/api/budget'),
    apiFetch('/api/obligations'),
  ]);

  const allExp   = allExpRes?.expenses || [];
  const filtered = allExp.filter(e => (e.date || '').startsWith(selectedMonth));
  reportExpenses = filtered;

  const spent   = filtered.reduce((s, e) => s + (e.amount || 0), 0);
  const budget  = budgetRes?.budget || 0;
  const saved   = budget > 0 && budget > spent ? budget - spent : 0;
  const pending = (oblRes?.obligations || []).filter(o => o.status !== 'paid').length;

  reportData = {
    spent, budget, saved, pending,
    month: selectedMonth,
    expenses: filtered,
    user: appState.user,
  };

  // KPIs
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('rpt-spent', fmt(spent));
  set('rpt-saved', saved > 0 ? fmt(saved) : '—');
  set('rpt-count', filtered.length);
  set('rpt-bills', pending);

  const label = new Date(selectedMonth + '-02').toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
  const rptLabel = document.getElementById('rpt-month-label');
  if (rptLabel) rptLabel.textContent = label;

  // Category donut chart
  const catTotals = {};
  filtered.forEach(e => { catTotals[e.category || 'Other'] = (catTotals[e.category || 'Other'] || 0) + e.amount; });
  if (Object.keys(catTotals).length)
    buildDonut('chart-rpt-cat', Object.keys(catTotals), Object.values(catTotals));

  // Budget usage donut
  const canvas = document.getElementById('chart-rpt-budget');
  if (canvas) {
    if (charts['chart-rpt-budget']) charts['chart-rpt-budget'].destroy();
    const spentV  = Math.round(spent);
    const budgetV = budget > 0 ? Math.round(budget) : Math.round(spent * 1.2) || 1;
    const savedV  = Math.max(0, budgetV - spentV);
    const over    = spentV > budgetV && budget > 0;
    charts['chart-rpt-budget'] = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Spent', budget > 0 ? 'Remaining' : 'No Budget Set'],
        datasets: [{ data: [spentV, savedV], backgroundColor: [over ? '#EF4444' : '#4F8EF7', getChartTheme().donutBorder],
          borderWidth: 0, hoverOffset: 6, cutout: '68%' }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: getChartTheme().legendColor, usePointStyle: true, font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => ' Rs.' + ctx.raw.toLocaleString('en-IN') } }
        }
      }
    });
  }

  // Populate category filter + render table
  const catSel = document.getElementById('rpt-cat-filter');
  if (catSel) {
    const cats = [...new Set(filtered.map(e => e.category).filter(Boolean))].sort();
    catSel.innerHTML = '<option value="">All Categories</option>' +
      cats.map(c => `<option value="${c}">${c}</option>`).join('');
  }
  const cb = document.getElementById('rpt-txn-count');
  if (cb) cb.textContent = filtered.length;
  renderReportTable(filtered);
}

function filterReportTable() {
  const q   = (document.getElementById('rpt-search')?.value || '').toLowerCase();
  const cat = document.getElementById('rpt-cat-filter')?.value || '';
  const filtered = reportExpenses.filter(e =>
    (!q || e.description.toLowerCase().includes(q)) &&
    (!cat || e.category === cat)
  );
  renderReportTable(filtered);
  const cb = document.getElementById('rpt-txn-count');
  if (cb) cb.textContent = filtered.length;
}

function renderReportTable(rows) {
  const tbody = document.getElementById('rpt-table-body');
  if (!tbody) return;
  tbody.innerHTML = rows.length ? rows.map(e => `
    <tr>
      <td>${formatDate(e.date)}</td>
      <td style="color:var(--text);font-weight:500;">${e.description}</td>
      <td>${catBadge(e.category)}</td>
      <td style="color:var(--text-muted);">${e.payment_method || '—'}</td>
      <td style="text-align:right;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--text);">
        ${fmtFull(e.amount)}
      </td>
    </tr>`).join('')
  : '<tr><td colspan="5" class="tbl-empty">No transactions found</td></tr>';
}

async function generateReport() {
  if (!reportData) { toast('Load the report page first', 'error'); return; }
  toast('Generating PDF report...', 'info');

  try {
    // jsPDF v2 access (CDN loaded as window.jspdf)
    const jsPDFLib = window.jspdf || window;
    const jsPDF    = jsPDFLib.jsPDF || jsPDFLib.jsPDF;
    if (typeof jsPDF !== 'function') {
      toast('PDF library not available. Try refreshing the page.', 'error');
      return;
    }

    const doc   = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
    const W     = 210;
    const user  = reportData.user || {};
    const month = new Date(reportData.month + '-01')
                    .toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });

    // Helper: jsPDF-safe color setters (always 3 separate numbers, never array, no alpha)
    const fill  = (r, g, b) => doc.setFillColor(r, g, b);
    const text  = (r, g, b) => doc.setTextColor(r, g, b);
    const fsize = (n)       => doc.setFontSize(n);
    const font  = (s, w)    => doc.setFont('helvetica', w || 'normal');

    // Helper: rupee sign (Rs.) since jsPDF helvetica has no Unicode rupee glyph
    const rs = (n) => 'Rs.' + parseFloat(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const rsInt = (n) => 'Rs.' + Math.round(n || 0).toLocaleString('en-IN');

    // ── PAGE 1: HEADER ────────────────────────────────────
    fill(15, 18, 32); doc.rect(0, 0, W, 42, 'F');

    fill(79, 142, 247); doc.roundedRect(14, 10, 22, 22, 3, 3, 'F');
    text(255, 255, 255); fsize(13); font('bold');
    doc.text('SF', 25, 25, { align: 'center' });

    fsize(17); font('bold');
    text(237, 240, 255);
    doc.text('SmartFinance Brain', 42, 20);

    fsize(9); font('normal');
    text(138, 156, 196);
    doc.text('Monthly Financial Report', 42, 27);
    doc.text('Generated: ' + new Date().toLocaleDateString('en-IN'), 42, 33);

    fill(79, 142, 247); doc.roundedRect(140, 13, 56, 15, 3, 3, 'F');
    text(255, 255, 255); fsize(10); font('bold');
    doc.text(month, 168, 23, { align: 'center' });

    let y = 52;

    // ── USER INFO BOX ─────────────────────────────────────
    fill(20, 26, 44); doc.roundedRect(14, y - 6, W - 28, 22, 3, 3, 'F');
    fsize(11); font('bold'); text(237, 240, 255);
    doc.text(user.name || 'User', 22, y + 2);
    font('normal'); fsize(9); text(138, 156, 196);
    if (user.phone) doc.text('Phone: ' + user.phone,        22, y + 9);
    if (user.email) doc.text('Email: ' + user.email,        90, y + 9);
    y += 28;

    // ── KPI CARDS ─────────────────────────────────────────
    const savedVal = (reportData.saved || 0) > 0 ? rs(reportData.saved) : '--';
    const kpis = [
      { label: 'Total Spent',   val: rs(reportData.spent),              r:79,  g:142, b:247 },
      { label: 'Total Saved',   val: savedVal,                           r:16,  g:185, b:129 },
      { label: 'Budget Set',    val: reportData.budget ? rs(reportData.budget) : 'Not set', r:139, g:92, b:246 },
      { label: 'Bills Pending', val: String(reportData.pending || 0),   r:245, g:158, b:11  },
      { label: 'Transactions',  val: String((reportData.expenses || []).length), r:6, g:182, b:212 },
    ];
    const kW = (W - 28 - (kpis.length - 1) * 3) / kpis.length;
    kpis.forEach((k, i) => {
      const kx = 14 + i * (kW + 3);
      fill(20, 26, 44); doc.roundedRect(kx, y, kW, 28, 2, 2, 'F');
      fill(k.r, k.g, k.b); doc.roundedRect(kx, y, kW, 3, 2, 2, 'F');
      fsize(7.5); font('normal'); text(138, 156, 196);
      doc.text(k.label, kx + kW / 2, y + 12, { align: 'center' });
      fsize(10); font('bold'); text(237, 240, 255);
      doc.text(k.val, kx + kW / 2, y + 22, { align: 'center' });
    });
    y += 36;

    // ── CATEGORY BREAKDOWN ────────────────────────────────
    fsize(12); font('bold'); text(237, 240, 255);
    doc.text('Spending by Category', 14, y); y += 8;

    const catTotals = {};
    (reportData.expenses || []).forEach(e => {
      catTotals[e.category || 'Other'] = (catTotals[e.category || 'Other'] || 0) + (e.amount || 0);
    });
    const sortedCats = Object.entries(catTotals).sort((a, b) => b[1] - a[1]);
    const colPalette = [
      [79,142,247],[139,92,246],[16,185,129],
      [245,158,11],[239,68,68],[6,182,212],[236,72,153],[249,115,22]
    ];
    const totalSp = reportData.spent || 1;

    sortedCats.forEach(([cat, amt], i) => {
      if (y > 238) return;
      const pct  = (amt / totalSp * 100).toFixed(1);
      const barW = Math.max(Math.round((amt / totalSp) * 100), 3);
      const col  = colPalette[i % colPalette.length];

      fill(26, 34, 54); doc.roundedRect(14, y, W - 28, 8, 1, 1, 'F');
      fill(col[0], col[1], col[2]); doc.roundedRect(14, y, barW, 8, 1, 1, 'F');
      fsize(8); font('bold'); text(255, 255, 255);
      doc.text(cat, 17, y + 5.5);
      font('normal');
      doc.text(rsInt(amt) + '  (' + pct + '%)', W - 16, y + 5.5, { align: 'right' });
      y += 11;
    });
    y += 6;

    // ── PENDING BILLS ─────────────────────────────────────
    const billsRes    = await apiFetch('/api/obligations');
    const pendingBills = (billsRes?.obligations || []).filter(o => o.status !== 'paid');

    if (pendingBills.length > 0 && y < 248) {
      fsize(12); font('bold'); text(237, 240, 255);
      doc.text('Pending Bills & Dues', 14, y); y += 8;

      pendingBills.slice(0, 8).forEach(b => {
        if (y > 268) return;
        const today     = new Date().toISOString().slice(0, 10);
        const isOverdue = b.due_date && b.due_date < today;

        fill(20, 26, 44); doc.roundedRect(14, y, W - 28, 9, 1, 1, 'F');
        if (isOverdue) { fill(239, 68, 68); doc.roundedRect(14, y, 2, 9, 0, 0, 'F'); }

        fsize(8); font('bold');
        text(isOverdue ? 248 : 237, isOverdue ? 113 : 240, isOverdue ? 113 : 255);
        doc.text((b.name || 'Unknown').slice(0, 35), 18, y + 6.3);

        font('normal'); text(138, 156, 196);
        doc.text('Due: ' + (b.due_date || '--'), 105, y + 6.3);

        font('bold'); text(237, 240, 255);
        doc.text(rsInt(b.amount || 0), W - 16, y + 6.3, { align: 'right' });
        y += 12;
      });
      y += 4;
    }

    // ── PAGE 2: TRANSACTIONS TABLE ────────────────────────
    if ((reportData.expenses || []).length > 0) {
      doc.addPage();
      fill(15, 18, 32); doc.rect(0, 0, W, 20, 'F');
      fsize(12); font('bold'); text(237, 240, 255);
      doc.text('All Transactions - ' + month, 14, 13);
      fsize(9); font('normal'); text(138, 156, 196);
      doc.text((reportData.expenses.length) + ' records', W - 14, 13, { align: 'right' });

      y = 26;
      fill(26, 34, 56); doc.rect(14, y, W - 28, 8, 'F');
      fsize(8); font('bold'); text(138, 156, 196);
      ['Date', 'Description', 'Category', 'Method', 'Amount'].forEach((h, i) => {
        const xPos = [18, 43, 103, 143, W - 16][i];
        const align = i === 4 ? 'right' : 'left';
        doc.text(h, xPos, y + 5.5, { align });
      });
      y += 10;

      reportData.expenses.forEach((e, idx) => {
        if (y > 276) { doc.addPage(); y = 14; }
        if (idx % 2 === 0) { fill(20, 26, 44); doc.rect(14, y - 1, W - 28, 7, 'F'); }
        fsize(7.5); font('normal'); text(200, 210, 240);
        const desc = (e.description || '').length > 28 ? (e.description || '').slice(0, 26) + '..' : (e.description || '--');
        doc.text(formatDate(e.date),                    18,     y + 4);
        doc.text(desc,                                  43,     y + 4);
        doc.text((e.category || '--').slice(0, 18),    103,    y + 4);
        doc.text((e.payment_method || '--').slice(0,12),143,   y + 4);
        font('bold'); text(237, 240, 255);
        doc.text(rsInt(e.amount), W - 16, y + 4, { align: 'right' });
        y += 7;
      });

      y += 4;
      fill(79, 142, 247); doc.rect(14, y, W - 28, 9, 'F');
      fsize(10); font('bold'); text(255, 255, 255);
      doc.text('TOTAL', 18, y + 6.3);
      doc.text(rsInt(reportData.spent), W - 16, y + 6.3, { align: 'right' });
    }

    // ── FOOTER ON EVERY PAGE ──────────────────────────────
    const totalPages = doc.getNumberOfPages();
    for (let p = 1; p <= totalPages; p++) {
      doc.setPage(p);
      fsize(7.5); font('normal'); text(62, 80, 112);
      doc.text('SmartFinance Brain - Personal Finance Report - Confidential', 14, 292);
      doc.text('Page ' + p + ' of ' + totalPages, W - 14, 292, { align: 'right' });
    }

    const safeName  = (user.name || 'user').replace(/[^a-zA-Z0-9]/g, '_');
    const filename  = 'SmartFinance_' + reportData.month + '_' + safeName + '.pdf';
    doc.save(filename);
    toast('PDF downloaded successfully!', 'success');

  } catch (err) {
    console.error('PDF generation error:', err);
    toast('PDF error: ' + (err.message || String(err)), 'error');
  }
}

// ══════════════════════════════════════════════════════════
//  QUICK STATS — add bills due count
// ══════════════════════════════════════════════════════════
async function loadQuickStatsFull() {
  const [dash, obl] = await Promise.all([
    apiFetch('/api/dashboard'),
    apiFetch('/api/obligations'),
  ]);
  if (!dash) return;
  document.getElementById('qs-alltime').textContent = fmt(dash.all_time_total);
  document.getElementById('qs-month').textContent   = fmt(dash.month_total);
  document.getElementById('qs-entries').textContent = dash.total_count || 0;
  const pending = (obl?.obligations || []).filter(o => o.status === 'pending').length;
  const qs = document.getElementById('qs-bills');
  if (qs) qs.textContent = pending;
}

// ══════════════════════════════════════════════════════════
//  IMPORTED FILES MANAGER
// ══════════════════════════════════════════════════════════
async function loadImportedFiles() {
  const data = await apiFetch('/api/import/files');
  const files = data?.files || [];

  const container = document.getElementById('imported-files-list');
  if (!container) return;

  if (!files.length) {
    container.innerHTML = `
      <div style="text-align:center;padding:40px 20px;color:var(--text-dim);">
        <i class="fas fa-folder-open" style="font-size:2.5rem;margin-bottom:12px;display:block;opacity:0.4;"></i>
        <div style="font-size:0.9rem;margin-bottom:6px;">No imported files yet</div>
        <div style="font-size:0.78rem;">Import CSV, Excel or text files from the <strong>Expenses → Import</strong> tab.</div>
      </div>`;
    return;
  }

  // Group by type
  const groups = { image: [], document: [], dataset: [], other: [] };
  const imgExts = ['jpg','jpeg','png','bmp','tiff','webp','gif'];
  const docExts = ['pdf','docx','txt','md'];
  const dataExts= ['xlsx','xls','csv'];

  files.forEach(f => {
    const ext = (f.filename || '').split('.').pop().toLowerCase();
    if (imgExts.includes(ext))  groups.image.push(f);
    else if (docExts.includes(ext)) groups.document.push(f);
    else if (dataExts.includes(ext)) groups.dataset.push(f);
    else groups.other.push(f);
  });

  const typeIcon = { image:'🖼️', document:'📄', dataset:'📊', other:'📁' };
  const typeLabel = { image:'Images & Receipts', document:'Bills & Documents', dataset:'Datasets (Excel/CSV)', other:'Other Files' };
  const typeBadge = { image:'badge-purple', document:'badge-blue', dataset:'badge-green', other:'badge-gray' };

  let html = `<div style="font-size:0.78rem;color:var(--text-dim);margin-bottom:14px;">${files.length} file(s) imported</div>`;

  Object.entries(groups).forEach(([type, arr]) => {
    if (!arr.length) return;
    html += `
      <div style="margin-bottom:18px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:0.78rem;font-weight:700;color:var(--text-muted);letter-spacing:0.08em;text-transform:uppercase;">
          <span>${typeIcon[type]}</span>${typeLabel[type]}
          <span style="background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:1px 8px;font-size:0.68rem;">${arr.length}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;">
          ${arr.map(f => `
            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:12px 16px;display:flex;align-items:center;gap:12px;transition:all 0.18s;" id="ifile-${f.id}">
              <div style="font-size:1.4rem;flex-shrink:0;">${typeIcon[type]}</div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:0.86rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${f.filename}</div>
                <div style="font-size:0.74rem;color:var(--text-dim);margin-top:2px;display:flex;gap:10px;flex-wrap:wrap;">
                  ${f.import_date ? `<span>📅 ${f.import_date.slice(0,10)}</span>` : ''}
                  ${f.rows_imported ? `<span>📝 ${f.rows_imported} expenses imported</span>` : ''}
                  ${f.file_size ? `<span>💾 ${Math.round(f.file_size/1024)}KB</span>` : ''}
                  <span style="background:rgba(79,142,247,0.1);color:var(--accent);border-radius:8px;padding:1px 8px;font-size:0.68rem;font-weight:700;">${(f.file_type||type).toUpperCase()}</span>
                </div>
              </div>
              <button onclick="deleteImportedFile(${f.id}, '${(f.filename||'').replace(/'/g,"\'")}', ${f.rows_imported||0})"
                title="Delete file ${f.rows_imported ? '+ its imported expenses' : ''}"
                style="flex-shrink:0;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:8px;color:#F87171;padding:7px 12px;cursor:pointer;font-size:0.78rem;font-weight:600;transition:all 0.15s;white-space:nowrap;">
                <i class="fas fa-trash-can"></i>${f.rows_imported ? ` + ${f.rows_imported} exp` : ''}
              </button>
            </div>`).join('')}
        </div>
      </div>`;
  });
  container.innerHTML = html;
}

async function deleteImportedFile(fileId, filename, rowCount) {
  const msg = rowCount
    ? `Delete "${filename}" and its ${rowCount} imported expenses?`
    : `Delete "${filename}"?`;
  if (!confirm(msg)) return;
  const res = await apiFetch(`/api/import/files/${fileId}`, { method: 'DELETE' });
  if (res?.success || res !== null) {
    document.getElementById(`ifile-${fileId}`)?.remove();
    toast(`Deleted "${filename}"${rowCount ? ` + ${rowCount} expenses` : ''}`, 'success');
    loadExpenses(); loadDashboard();
  } else {
    toast('Failed to delete file', 'error');
  }
}

// ══════════════════════════════════════════════════════════
//  IMPORT PREVIEW + EDIT
// ══════════════════════════════════════════════════════════
let previewData = null; // { headers, rows } editable

async function previewImportFile(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(API_BASE + '/api/import/preview', { method: 'POST', body: fd });
  const data = res.ok ? await res.json() : null;
  if (!data?.rows?.length) {
    document.getElementById('import-result').innerHTML =
      '<div class="alert-box alert-error show">Could not parse file. Check format.</div>';
    return;
  }
  previewData = { headers: data.headers || [], rows: data.rows.map(r => [...r]), filename: file.name, file };
  renderImportPreview();
  document.getElementById('import-preview-section').style.display = 'block';
  document.getElementById('import-result').innerHTML = '';
}

function renderImportPreview() {
  if (!previewData) return;
  const { headers, rows } = previewData;
  const container = document.getElementById('import-preview-table-wrap');
  if (!container) return;
  const total = rows.length;

  let html = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
      <div style="font-size:0.82rem;color:var(--text-muted);">
        📊 <strong style="color:var(--text);">${total}</strong> rows · Click any cell to edit
      </div>
      <div style="display:flex;gap:8px;">
        <button class="tbl-btn" onclick="addPreviewRow()"><i class="fas fa-plus"></i> Add Row</button>
        <button class="tbl-btn tbl-btn-accent" onclick="confirmImportPreview()"><i class="fas fa-file-import"></i> Import All (${total})</button>
        <button class="btn-ghost" style="padding:6px 12px;font-size:0.8rem;border-radius:8px;" onclick="cancelImportPreview()">Cancel</button>
      </div>
    </div>
    <div style="overflow-x:auto;border-radius:12px;border:1px solid var(--border);">
    <table class="data-table" style="min-width:700px;">
      <thead><tr>
        <th style="width:36px;text-align:center;">#</th>
        ${headers.map(h => `<th>${h}</th>`).join('')}
        <th style="width:40px;"></th>
      </tr></thead>
      <tbody>
        ${rows.map((row, ri) => `
          <tr id="prev-row-${ri}">
            <td style="text-align:center;color:var(--text-dim);font-size:0.74rem;">${ri+1}</td>
            ${row.map((cell, ci) => `
              <td style="padding:0;">
                <input type="text" value="${String(cell||'').replace(/"/g,'&quot;')}"
                  onchange="updatePreviewCell(${ri},${ci},this.value)"
                  style="width:100%;background:transparent;border:none;padding:9px 12px;
                    font-size:0.82rem;color:var(--text);font-family:inherit;cursor:pointer;"
                  onfocus="this.style.background='var(--surface3)';this.style.borderRadius='6px';"
                  onblur="this.style.background='transparent';">
              </td>`).join('')}
            <td style="text-align:center;">
              <button onclick="deletePreviewRow(${ri})" title="Remove row"
                style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:4px 8px;font-size:0.82rem;"
                onmouseover="this.style.color='#F87171'" onmouseout="this.style.color='var(--text-dim)'">
                <i class="fas fa-xmark"></i>
              </button>
            </td>
          </tr>`).join('')}
      </tbody>
    </table>
    </div>`;
  container.innerHTML = html;
}

function updatePreviewCell(row, col, val) {
  if (previewData) previewData.rows[row][col] = val;
}

function deletePreviewRow(ri) {
  if (!previewData) return;
  previewData.rows.splice(ri, 1);
  renderImportPreview();
}

function addPreviewRow() {
  if (!previewData) return;
  previewData.rows.push(Array(previewData.headers.length).fill(''));
  renderImportPreview();
  // Scroll to bottom of table
  const w = document.getElementById('import-preview-table-wrap');
  if (w) w.scrollTop = w.scrollHeight;
}

function cancelImportPreview() {
  previewData = null;
  document.getElementById('import-preview-section').style.display = 'none';
  document.getElementById('import-preview-table-wrap').innerHTML = '';
}

async function confirmImportPreview() {
  if (!previewData?.rows?.length) return;
  const fd = new FormData();
  // Rebuild CSV from edited data and send
  const csvLines = [previewData.headers.join(',')];
  previewData.rows.forEach(row => csvLines.push(row.map(c => `"${String(c||'').replace(/"/g,'""')}"`).join(',')));
  const csvBlob = new Blob([csvLines.join('\n')], { type: 'text/csv' });
  const csvFile = new File([csvBlob], previewData.filename || 'edited_import.csv', { type: 'text/csv' });
  fd.append('file', csvFile);

  const submitBtn = document.querySelector('[onclick="confirmImportPreview()"]');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Importing...'; }

  const res  = await fetch(API_BASE + '/api/import', { method: 'POST', body: fd });
  const data = res.ok ? await res.json() : null;
  const msg  = data?.message || `Imported from ${previewData.filename}`;

  if (submitBtn) { submitBtn.disabled = false; }
  document.getElementById('import-result').innerHTML =
    `<div class="alert-box ${data?.success ? 'alert-success' : 'alert-error'} show">${msg}</div>`;
  toast(msg, data?.success ? 'success' : 'error');

  if (data?.success) {
    cancelImportPreview();
    loadExpenses(); loadDashboard(); loadImportedFiles();
    checkEmailAlerts();
  }
}

// ══════════════════════════════════════════════════════════
//  INIT — add theme init call
// ══════════════════════════════════════════════════════════


// Inject styles for preview edit table buttons (runs once)
(function injectPreviewStyles() {
  if (document.getElementById('sfb-preview-styles')) return;
  const s = document.createElement('style');
  s.id = 'sfb-preview-styles';
  s.textContent = `
    .tbl-btn { background: var(--surface2,#1C2230); border:1px solid var(--border,#21262D); border-radius:8px; color:var(--text,#E6EDF3); padding:7px 14px; font-size:0.8rem; font-weight:600; cursor:pointer; transition:all 0.15s; display:inline-flex; align-items:center; gap:6px; }
    .tbl-btn:hover { border-color:var(--accent,#4F8EF7); color:var(--accent,#4F8EF7); }
    .tbl-btn-accent { background:rgba(79,142,247,0.12); border-color:rgba(79,142,247,0.3); color:var(--accent,#4F8EF7); }
    .tbl-btn-accent:hover { background:rgba(79,142,247,0.22); }
  `;
  document.head.appendChild(s);
})();