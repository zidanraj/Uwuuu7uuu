// static/app.js — Z3NITH UWU PANEL frontend logic

const socket = io();

let accounts    = [];
let allStats    = {};
let accountStats = {};

// ---- NAV ----
document.querySelectorAll('.nav-links li').forEach(li => {
  li.addEventListener('click', () => {
    document.querySelectorAll('.nav-links li').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    li.classList.add('active');
    document.getElementById('tab-' + li.dataset.tab).classList.add('active');
  });
});

// ---- PARTICLES ----
(function spawnParticles() {
  const container = document.getElementById('particles');
  const colors = ['#7c3aed','#06b6d4','#8b5cf6','#10b981'];
  for (let i = 0; i < 40; i++) {
    const p = document.createElement('div');
    p.classList.add('particle');
    const size = Math.random() * 4 + 2;
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random()*100}%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-duration:${Math.random()*20+10}s;
      animation-delay:-${Math.random()*20}s;
    `;
    container.appendChild(p);
  }
})();

// ---- SOCKET EVENTS ----
socket.on('accounts_updated', data => {
  accounts = data;
  renderAccountsTable();
  updateDashboardStats();
});

socket.on('account_stats', data => {
  accountStats[data.id] = data.stats;
  updateDashboardStats();
  updateAccountBoard();
});

socket.on('stats_update', data => {
  allStats = data;
  updateDashboardStats();
});

socket.on('log', data => {
  appendLog(`[Acc ${data.id}] ${data.msg}`, data.msg);
});

// ---- DASHBOARD ----
function updateDashboardStats() {
  const total   = accounts.length;
  let running   = 0, hunts = 0, battles = 0, cmds = 0, captchas = 0;
  Object.values(accountStats).forEach(s => {
    if (s.status === 'running' || s.status === 'captcha') running++;
    hunts    += s.hunts    || 0;
    battles  += s.battles  || 0;
    cmds     += s.commands || 0;
    captchas += s.captchas || 0;
  });
  document.getElementById('statTotal').textContent    = total;
  document.getElementById('statRunning').textContent  = running;
  document.getElementById('statHunts').textContent    = hunts;
  document.getElementById('statBattles').textContent  = battles;
  document.getElementById('statCommands').textContent = cmds;
  document.getElementById('statCaptchas').textContent = captchas;

  const dot  = document.getElementById('globalStatus');
  const text = document.getElementById('globalStatusText');
  if (running > 0) {
    dot.className  = 'status-dot running';
    text.textContent = `${running} running`;
  } else {
    dot.className  = 'status-dot';
    text.textContent = 'Idle';
  }
}

function updateAccountBoard() {
  const board = document.getElementById('accountBoard');
  if (!accounts.length) {
    board.innerHTML = '<div class="empty-state">No accounts running. Add accounts first.</div>';
    return;
  }
  board.innerHTML = accounts.map(acc => {
    const s   = accountStats[acc.id] || {};
    const cls = s.status === 'running' ? 'running' : s.status === 'captcha' ? 'captcha' : '';
    const badge = s.status === 'running'
      ? '<span class="badge badge-running">RUNNING</span>'
      : s.status === 'captcha'
      ? '<span class="badge badge-captcha">CAPTCHA</span>'
      : '<span class="badge badge-stopped">STOPPED</span>';
    return `
      <div class="acc-mini-card ${cls}">
        <div class="acc-mini-name">${escHtml(acc.name)}</div>
        ${badge}
        <div class="acc-mini-stat" style="margin-top:8px">
          🎯 ${s.hunts||0} hunts &nbsp; ⚔️ ${s.battles||0} battles
        </div>
        <div class="acc-mini-stat">💰 ${s.balance||0} cwy</div>
      </div>`;
  }).join('');
}

// ---- ACCOUNTS TABLE ----
function renderAccountsTable() {
  const tbody = document.getElementById('accountsBody');
  if (!accounts.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No accounts configured.</td></tr>';
    return;
  }
  tbody.innerHTML = accounts.map((acc, i) => {
    const s     = accountStats[acc.id] || {};
    const badge = s.status === 'running'
      ? '<span class="badge badge-running">RUNNING</span>'
      : s.status === 'captcha'
      ? '<span class="badge badge-captcha">CAPTCHA</span>'
      : '<span class="badge badge-stopped">STOPPED</span>';
    const proxy = acc.proxy ? acc.proxy.substring(0,20)+'…' : '—';
    return `
      <tr>
        <td>${i+1}</td>
        <td><b>${escHtml(acc.name)}</b></td>
        <td><code>${acc.channel_id}</code></td>
        <td>${proxy}</td>
        <td>${badge}</td>
        <td>${s.hunts||0}</td>
        <td>${s.balance||0}</td>
        <td>
          <div class="btn-group">
            <button class="btn btn-green" style="padding:6px 12px;font-size:11px" onclick="startAcc(${acc.id})">▶</button>
            <button class="btn btn-red"   style="padding:6px 12px;font-size:11px" onclick="stopAcc(${acc.id})">■</button>
            <button class="btn" style="padding:6px 12px;font-size:11px;background:rgba(239,68,68,0.2);color:#ef4444" onclick="deleteAcc(${acc.id})">✕</button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

// ---- ACCOUNT ACTIONS ----
async function startAcc(id)   { await api(`/api/start/${id}`,   'POST'); }
async function stopAcc(id)    { await api(`/api/stop/${id}`,    'POST'); }
async function deleteAcc(id)  {
  if (!confirm('Delete this account?')) return;
  await api(`/api/accounts/${id}`, 'DELETE');
}
async function startAll() { await api('/api/start_all', 'POST'); }
async function stopAll()  { await api('/api/stop_all',  'POST'); }

function openAddModal() {
  document.getElementById('addModal').classList.add('open');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

async function addAccount() {
  const name    = document.getElementById('newName').value.trim();
  const token   = document.getElementById('newToken').value.trim();
  const channel = document.getElementById('newChannel').value.trim();
  const proxy   = document.getElementById('newProxy').value.trim();
  if (!name || !token || !channel) { alert('Name, token, channel required'); return; }
  await api('/api/accounts', 'POST', { name, token, channel_id: channel, proxy });
  closeModal('addModal');
  document.getElementById('newName').value  = '';
  document.getElementById('newToken').value = '';
  document.getElementById('newChannel').value = '';
  document.getElementById('newProxy').value = '';
  loadAccounts();
}

// ---- GIVE ALL ----
async function giveAll() {
  const uid    = document.getElementById('giveUID').value.trim();
  const amount = parseInt(document.getElementById('giveAmount').value);
  if (!uid || !amount) { alert('UID and amount required'); return; }
  const result = await api('/api/give_all', 'POST', { target_uid: uid, amount });
  const box = document.getElementById('giveResult');
  box.style.display = 'block';
  box.innerHTML = '<b>Results:</b><br>' +
    Object.entries(result).map(([id, r]) => `Account ${id}: ${r}`).join('<br>');
}

// ---- CAPTCHA KEYS ----
async function loadCaptchaKeys() {
  const keys  = await api('/api/captcha_keys', 'GET');
  const tbody = document.getElementById('keysBody');
  if (!keys || !keys.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No keys. Bot pauses on captcha without them.</td></tr>';
    return;
  }
  tbody.innerHTML = keys.map((k, i) => `
    <tr>
      <td>${i+1}</td>
      <td><span class="badge badge-running">${k.provider}</span></td>
      <td><code>${k.key.substring(0,8)}${'*'.repeat(16)}${k.key.slice(-4)}</code></td>
      <td><button class="btn btn-red" style="padding:5px 12px;font-size:11px" onclick="deleteKey(${k.id})">DEL</button></td>
    </tr>`).join('');
}

function openAddKeyModal() {
  document.getElementById('addKeyModal').classList.add('open');
}
async function addKey() {
  const key      = document.getElementById('newKey').value.trim();
  const provider = document.getElementById('newKeyProvider').value;
  if (!key) { alert('Key required'); return; }
  await api('/api/captcha_keys', 'POST', { key, provider });
  closeModal('addKeyModal');
  document.getElementById('newKey').value = '';
  loadCaptchaKeys();
}
async function deleteKey(id) {
  await api(`/api/captcha_keys/${id}`, 'DELETE');
  loadCaptchaKeys();
}

// ---- SETTINGS ----
async function loadSettings() {
  const s = await api('/api/settings', 'GET');
  if (!s) return;
  const fields = [
    'sell_interval_minutes','sell_what',
    'hunt_min_delay','hunt_max_delay',
  ];
  fields.forEach(f => {
    const el = document.getElementById('set_' + f);
    if (el) el.value = s[f] ?? el.value;
  });
  const checks = ['hunt_enabled','battle_enabled','pray_enabled','curse_enabled','daily_enabled'];
  checks.forEach(f => {
    const el = document.getElementById('set_' + f);
    if (el) el.checked = (s[f] === '1');
  });
}

async function saveSettings() {
  const data = {};
  ['sell_interval_minutes','sell_what','hunt_min_delay','hunt_max_delay'].forEach(f => {
    const el = document.getElementById('set_' + f);
    if (el) data[f] = el.value;
  });
  ['hunt_enabled','battle_enabled','pray_enabled','curse_enabled','daily_enabled'].forEach(f => {
    const el = document.getElementById('set_' + f);
    if (el) data[f] = el.checked ? '1' : '0';
  });
  await api('/api/settings', 'POST', data);
  flashMsg('Settings saved!');
}

// ---- LOGS ----
function appendLog(msg, raw='') {
  const box  = document.getElementById('logBox');
  const line = document.createElement('div');
  line.classList.add('log-line');
  if (raw.toLowerCase().includes('captcha')) line.classList.add('captcha');
  if (raw.toLowerCase().includes('error'))   line.classList.add('error');
  if (raw.toLowerCase().includes('solved') || raw.toLowerCase().includes('ok')) line.classList.add('success');
  const ts = new Date().toTimeString().slice(0,8);
  line.textContent = `[${ts}] ${msg}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
  // cap at 500 lines
  while (box.children.length > 500) box.removeChild(box.firstChild);
}
function clearLogs() { document.getElementById('logBox').innerHTML = ''; }

// ---- HELPERS ----
async function api(url, method='GET', body=null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(url, opts);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      appendLog(`API error ${r.status}: ${err.error || r.statusText}`, 'error');
      return null;
    }
    return r.json();
  } catch (e) {
    appendLog(`Network error: ${e.message}`, 'error');
    return null;
  }
}

async function loadAccounts() {
  const data = await api('/api/accounts', 'GET');
  if (data) {
    accounts = data;
    renderAccountsTable();
    updateAccountBoard();
    updateDashboardStats();
  }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function flashMsg(msg) {
  const el = document.createElement('div');
  el.textContent = msg;
  el.style.cssText = `
    position:fixed; bottom:24px; right:24px;
    background:rgba(16,185,129,0.9); color:#fff;
    padding:12px 20px; border-radius:8px;
    font-weight:700; font-size:13px; letter-spacing:1px;
    z-index:200; animation: fadeInOut 2.5s forwards;
  `;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

// ---- INIT ----
loadAccounts();
loadCaptchaKeys();
loadSettings();
