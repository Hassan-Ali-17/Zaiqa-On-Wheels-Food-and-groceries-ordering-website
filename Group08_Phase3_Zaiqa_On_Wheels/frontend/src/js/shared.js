// ── API Base URL ─────────────────────────────────────────────────────────────
// Auto-detects whether we're served from Flask (port 5000) or standalone
const API = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
  ? 'http://127.0.0.1:5000/api'
  : '/api';

// ── Login redirect path ───────────────────────────────────────────────────────
// When served from Flask: '/' is the login page
// When opened as file: needs relative path
function getLoginPath() {
  if (window.location.protocol === 'file:') {
    // opened directly as file — climb up to root
    const depth = (window.location.pathname.match(/\//g) || []).length - 1;
    return '../'.repeat(Math.max(0, depth - 1)) + 'index.html';
  }
  // served from Flask — always redirect to root
  return '/';
}

// ── Storage helpers ──────────────────────────────────────────────────────────
const store = {
  get: (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set: (k, v) => localStorage.setItem(k, JSON.stringify(v)),
  clear: () => localStorage.clear()
};

function getUser()  { return store.get('user'); }
function setUser(u) { store.set('user', u); }
function getToken() { return localStorage.getItem('qb_token') || null; }
function setToken(t){ localStorage.setItem('qb_token', t); }

// ── Auth guard ────────────────────────────────────────────────────────────────
function requireAuth(role) {
  const user = getUser();
  if (!user || !getToken()) {
    window.location.href = getLoginPath();
    return null;
  }
  if (role && user.role !== role) {
    window.location.href = getLoginPath();
    return null;
  }
  return user;
}

function requireAnyAuth(...roles) {
  const user = getUser();
  if (!user || !getToken()) {
    window.location.href = getLoginPath();
    return null;
  }
  if (roles.length && !roles.includes(user.role)) {
    window.location.href = getLoginPath();
    return null;
  }
  return user;
}

// ── API helper ────────────────────────────────────────────────────────────────
// Always attaches JWT Bearer token. Returns null on network error or 401.
async function api(method, path, body = null) {
  try {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(API + path, opts);

    // 401 = token expired/invalid → send to login
    if (res.status === 401) {
      store.clear();
      localStorage.removeItem('qb_token');
      window.location.href = getLoginPath();
      return null;
    }

    const text = await res.text();
    if (!text || !text.trim()) return null;

    try {
      return JSON.parse(text);
    } catch {
      console.error('API parse error:', method, path, text.substring(0, 100));
      return null;
    }
  } catch (e) {
    console.error('API error:', method, path, e.message);
    return null;
  }
}

const GET    = (path)       => api('GET',    path);
const POST   = (path, body) => api('POST',   path, body);
const PUT    = (path, body) => api('PUT',    path, body);
const DELETE = (path, body) => api('DELETE', path, body);

// ── Login helper — saves user + JWT token ─────────────────────────────────────
function saveLoginResponse(data) {
  if (data && data.token) {
    setToken(data.token);
    const user = {
      user_id:           data.user_id,
      name:              data.name,
      email:             data.email,
      phone:             data.phone || '',
      role:              data.role,
      rider_id:          data.rider_id,
      rider_status:      data.rider_status,
      restaurant_id:     data.restaurant_id,
      restaurant_name:   data.restaurant_name,
      restaurant_status: data.restaurant_status
    };
    setUser(user);
    return user;
  }
  return null;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
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

// ── Global loading spinner ────────────────────────────────────────────────────
function showLoading(show = true) {
  let el = document.getElementById('global-loader');
  if (!el) {
    el = document.createElement('div');
    el.id = 'global-loader';
    el.innerHTML = '<div class="loader-spinner"></div>';
    el.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:9999;align-items:center;justify-content:center;';
    document.body.appendChild(el);
  }
  el.style.display = show ? 'flex' : 'none';
}

// ── Status badge ──────────────────────────────────────────────────────────────
function statusBadge(status) {
  const map = {
    'Pending':          'badge-pending',
    'Confirmed':        'badge-confirmed',
    'Preparing':        'badge-preparing',
    'Out for Delivery': 'badge-delivery',
    'Delivered':        'badge-delivered',
    'Cancelled':        'badge-cancelled',
    'pending':          'badge-pending',
    'approved':         'badge-approved',
    'rejected':         'badge-rejected',
  };
  return `<span class="badge ${map[status] || 'badge-pending'}">${status}</span>`;
}

// ── Time helpers ──────────────────────────────────────────────────────────────
function timeAgo(dt) {
  if (!dt) return '';
  const diff = Date.now() - new Date(dt).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(dt).toLocaleDateString();
}

function formatDate(dt) {
  if (!dt) return '';
  return new Date(dt).toLocaleString();
}

// ── Modal helpers ─────────────────────────────────────────────────────────────
function openModal(id)  { const el = document.getElementById(id); if (el) el.classList.add('open');    }
function closeModal(id) { const el = document.getElementById(id); if (el) el.classList.remove('open'); }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Tabs ──────────────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group  = btn.dataset.group || 'default';
      const target = btn.dataset.tab;
      document.querySelectorAll(`.tab-btn[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
      document.querySelectorAll(`.tab-content[data-group="${group}"]`).forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const tc = document.querySelector(`.tab-content[data-tab="${target}"][data-group="${group}"]`);
      if (tc) tc.classList.add('active');
    });
  });
}

// ── Logout ────────────────────────────────────────────────────────────────────
async function logout() {
  try { await POST('/logout'); } catch(e) {}
  store.clear();
  localStorage.removeItem('qb_token');
  window.location.href = getLoginPath();
}

// ── Render navbar user badge ──────────────────────────────────────────────────
function renderUserBadge(containerId) {
  const user = getUser();
  if (!user) return;
  const el = document.getElementById(containerId);
  if (el) {
    el.innerHTML = `
      <span class="user-badge">${user.name}</span>
      <span class="role-badge" style="font-size:0.7rem;color:var(--text-muted);margin-right:0.5rem;">${user.role}</span>
      <button class="btn btn-outline btn-sm" onclick="logout()">Logout</button>
    `;
  }
}

// ── Cuisine emoji map ─────────────────────────────────────────────────────────
function cuisineEmoji(cuisine) {
  const map = {
    'Fast Food':'🍔','Italian':'🍕','Pakistani':'🍛',
    'Japanese':'🍣','Chinese':'🥡','BBQ':'🔥','Seafood':'🦐','Desserts':'🍰'
  };
  return map[cuisine] || '🍽️';
}

// ── Theme toggle ──────────────────────────────────────────────────────────────
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

document.addEventListener('DOMContentLoaded', initTheme);

// ── Promo helper ──────────────────────────────────────────────────────────────
async function validatePromo(code, orderTotal) {
  return await POST('/promo/validate', { code, order_total: orderTotal });
}

// ── Loyalty helper ────────────────────────────────────────────────────────────
async function getLoyalty(customerId) {
  return await GET(`/loyalty/${customerId}`);
}
