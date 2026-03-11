// API base - works whether opened via Flask (port 5000) or Live Server (port 5500)
const API = window.location.port === '5000' 
  ? '/api'  // served from Flask - same origin, zero CORS
  : 'http://127.0.0.1:5000/api'; // Live Server - cross origin

// ── Storage helpers ──────────────────────────────────────────────────────
const store = {
  get: (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set: (k, v) => localStorage.setItem(k, JSON.stringify(v)),
  clear: () => localStorage.clear()
};

function getUser() { return store.get('user'); }
function setUser(u) { store.set('user', u); }

// ── Auth guard ───────────────────────────────────────────────────────────
function requireAuth(role) {
  const user = getUser();
  if (!user) { window.location.href = '/frontend/index.html'; return null; }
  if (role && user.role !== role) {
    window.location.href = '/frontend/index.html';
    return null;
  }
  return user;
}

function requireAnyAuth(...roles) {
  const user = getUser();
  if (!user) { window.location.href = '/frontend/index.html'; return null; }
  if (roles.length && !roles.includes(user.role)) {
    window.location.href = '/frontend/index.html';
    return null;
  }
  return user;
}

// ── API helper ───────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    // Read as text first - res.json() throws on some browsers for 4xx CORS responses
    const text = await res.text();
    if (!text || !text.trim()) return null;
    return JSON.parse(text);
  } catch (e) {
    console.error('API error:', method, path, e);
    return null;
  }
}

const GET = (path) => api('GET', path);
const POST = (path, body) => api('POST', path, body);
const PUT = (path, body) => api('PUT', path, body);
const DELETE = (path, body) => api('DELETE', path, body);

// ── Toast ────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.className = `show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 3000);
}

// ── Status badge ─────────────────────────────────────────────────────────
function statusBadge(status) {
  const map = {
    'Pending': 'badge-pending',
    'Confirmed': 'badge-confirmed',
    'Preparing': 'badge-preparing',
    'Out for Delivery': 'badge-delivery',
    'Delivered': 'badge-delivered',
    'Cancelled': 'badge-cancelled',
    'pending': 'badge-pending',
    'approved': 'badge-approved',
    'rejected': 'badge-rejected',
  };
  return `<span class="badge ${map[status] || 'badge-pending'}">${status}</span>`;
}

// ── Time formatter ───────────────────────────────────────────────────────
function timeAgo(dt) {
  const diff = Date.now() - new Date(dt).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(dt).toLocaleDateString();
}

function formatDate(dt) {
  return new Date(dt).toLocaleString();
}

// ── Modal helpers ────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Tabs ─────────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.dataset.group || 'default';
      const target = btn.dataset.tab;
      document.querySelectorAll(`.tab-btn[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
      document.querySelectorAll(`.tab-content[data-group="${group}"]`).forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const tc = document.querySelector(`.tab-content[data-tab="${target}"][data-group="${group}"]`);
      if (tc) tc.classList.add('active');
    });
  });
}

// ── Logout ───────────────────────────────────────────────────────────────
async function logout() {
  try { await POST('/logout'); } catch(e) {}
  store.clear();
  // Calculate correct path back to login from any subfolder depth
  const path = window.location.pathname;
  if (path.includes('/pages/')) {
    window.location.href = '../../index.html';
  } else if (path.includes('/frontend/')) {
    window.location.href = 'index.html';
  } else {
    window.location.href = 'frontend/index.html';
  }
}

// ── Render navbar user info ───────────────────────────────────────────────
function renderUserBadge(containerId) {
  const user = getUser();
  if (!user) return;
  const el = document.getElementById(containerId);
  if (el) {
    el.innerHTML = `
      <span class="user-badge">${user.name}</span>
      <button class="btn btn-outline btn-sm" onclick="logout()">Logout</button>
    `;
  }
}

// ── Restaurant emoji map ─────────────────────────────────────────────────
function cuisineEmoji(cuisine) {
  const map = { 'Fast Food':'🍔','Italian':'🍕','Pakistani':'🍛','Japanese':'🍣','Chinese':'🥡','BBQ':'🔥','Seafood':'🦐','Desserts':'🍰' };
  return map[cuisine] || '🍽️';
}

// ── Theme Toggle (Dark / Light Mode) ─────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('qb_theme') || 'dark';
  if (saved === 'light') document.body.classList.add('light-mode');
  updateThemeBtn();
}

function toggleTheme() {
  document.body.classList.toggle('light-mode');
  const isLight = document.body.classList.contains('light-mode');
  localStorage.setItem('qb_theme', isLight ? 'light' : 'dark');
  updateThemeBtn();
}

function updateThemeBtn() {
  const isLight = document.body.classList.contains('light-mode');
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.innerHTML = isLight ? '🌙 Dark' : '☀️ Light';
}

// Auto-init theme on every page load
document.addEventListener('DOMContentLoaded', initTheme);

// ── Promo Code Helper ─────────────────────────────────────────────────────────
async function validatePromo(code, orderTotal) {
  const res = await fetch(`${API}/promo/validate`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({code, order_total: orderTotal})
  });
  return await res.json();
}

// ── Loyalty Points Helper ─────────────────────────────────────────────────────
async function getLoyalty(customerId) {
  return await GET(`/loyalty/${customerId}`);
}
