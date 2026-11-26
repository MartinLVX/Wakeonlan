'use strict';

const STORE_KEY = 'wol-relay';
const $ = (sel) => document.querySelector(sel);

const views = { devices: $('#devices-view'), settings: $('#settings-view') };
const msg = $('#message');
let statusTimer = null;
let fastUntil = 0;

// ---------- configuración guardada ----------

function loadSettings() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
    if (s && s.relay && s.token) return s;
  } catch (_) { /* almacenamiento no disponible */ }
  return null;
}

function saveSettings(s) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); } catch (_) { /* ignorar */ }
}

function cleanRelay(url) {
  return url.trim().replace(/\/+$/, '');
}

/** Lee "#relay=...&token=..." de un enlace de configuración. */
function parseSetupLink(text) {
  const i = text.indexOf('#');
  if (i < 0) return null;
  const p = new URLSearchParams(text.slice(i + 1));
  const relay = p.get('relay');
  const token = p.get('token');
  return relay && token ? { relay: cleanRelay(relay), token } : null;
}

/** Si la PWA la sirve el propio relay, ya sabemos su dirección. */
function guessRelay() {
  return location.hostname.endsWith('github.io') ? '' : location.origin;
}

// ---------- llamadas al relay ----------

async function api(path, options = {}) {
  const s = loadSettings();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  let res;
  try {
    res = await fetch(s.relay + path, {
      ...options,
      signal: ctrl.signal,
      headers: {
        Authorization: 'Bearer ' + s.token,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
    });
  } catch (e) {
    throw new Error(networkHint(s.relay, e));
  } finally {
    clearTimeout(timer);
  }
  let data = {};
  try { data = await res.json(); } catch (_) { /* sin cuerpo */ }
  if (!res.ok) throw new Error(data.error || `El relay respondió ${res.status}`);
  return data;
}

function networkHint(relay, e) {
  if (location.protocol === 'https:' && relay.startsWith('http:')) {
    return 'Esta página es HTTPS y el relay es HTTP, y el navegador bloquea esa mezcla. ' +
      'Abre la PWA desde el propio relay (su dirección http://…) o dale HTTPS al relay. Mira la guía.';
  }
  if (e && e.name === 'AbortError') {
    return 'El relay no contesta. ¿Está encendido y conectado? Si estás fuera de casa, ¿tienes Tailscale activo?';
  }
  return 'No se pudo conectar con el relay. Revisa la dirección y que Tailscale esté activo si estás fuera de casa.';
}

// ---------- interfaz ----------

function show(view) {
  for (const [name, el] of Object.entries(views)) el.hidden = name !== view;
  if (view !== 'devices') stopStatus();
}

function say(text, kind = '') {
  msg.textContent = text;
  msg.className = 'message ' + kind;
  msg.hidden = !text;
}

function openSettings() {
  const s = loadSettings();
  $('#relay-input').value = s ? s.relay : guessRelay();
  $('#token-input').value = s ? s.token : '';
  $('#link-input').value = '';
  $('#cancel-btn').hidden = !s;
  say('');
  show('settings');
}

async function loadDevices() {
  say('');
  const list = $('#devices');
  list.replaceChildren();
  show('devices');
  let data;
  try {
    data = await api('/api/devices');
  } catch (e) {
    say(e.message, 'error');
    return;
  }
  $('#empty').hidden = data.devices.length > 0;
  for (const dev of data.devices) list.append(renderDevice(dev));
  startStatus();
}

function renderDevice(dev) {
  const li = $('#device-tpl').content.firstElementChild.cloneNode(true);
  li.dataset.id = dev.id;
  li.dataset.hasStatus = dev.has_status ? '1' : '';
  li.querySelector('.name').textContent = dev.name;
  li.querySelector('.power').setAttribute('aria-label', 'Encender ' + dev.name);
  setState(li, dev.has_status ? null : undefined);
  li.querySelector('.power').addEventListener('click', () => wake(li, dev));
  return li;
}

/** online: true / false; null = comprobando; undefined = sin comprobación. */
function setState(li, online) {
  const dot = li.querySelector('.dot');
  const state = li.querySelector('.state');
  dot.className = 'dot' + (online === true ? ' on' : online === undefined ? ' unknown' : '');
  state.textContent = online === true ? 'Encendido'
    : online === false ? 'Apagado'
    : online === null ? 'Comprobando…' : '';
}

async function wake(li, dev) {
  const btn = li.querySelector('.power');
  btn.disabled = true;
  btn.classList.add('sending');
  if (navigator.vibrate) navigator.vibrate(30);
  try {
    await api('/api/wake', { method: 'POST', body: JSON.stringify({ id: dev.id }) });
    say(`Paquete enviado a ${dev.name}. Suele tardar entre 10 y 60 segundos en arrancar.`, 'ok');
    if (dev.has_status) {
      li.querySelector('.state').textContent = 'Arrancando…';
      fastUntil = Date.now() + 2 * 60 * 1000;
      startStatus();
    }
  } catch (e) {
    say(e.message, 'error');
  } finally {
    btn.classList.remove('sending');
    setTimeout(() => { btn.disabled = false; }, 3000);
  }
}

async function refreshStatus() {
  const items = [...document.querySelectorAll('.device')].filter((li) => li.dataset.hasStatus);
  await Promise.all(items.map(async (li) => {
    try {
      const r = await api('/api/status?id=' + encodeURIComponent(li.dataset.id));
      const booting = li.querySelector('.state').textContent === 'Arrancando…';
      if (r.online || !booting) setState(li, r.online);
    } catch (_) { /* se reintenta en la siguiente vuelta */ }
  }));
}

function startStatus() {
  stopStatus();
  if (!document.querySelector('.device[data-has-status="1"]')) return;
  const tick = async () => {
    if (document.visibilityState === 'visible') await refreshStatus();
    statusTimer = setTimeout(tick, Date.now() < fastUntil ? 3000 : 15000);
  };
  tick();
}

function stopStatus() {
  clearTimeout(statusTimer);
  statusTimer = null;
}

// ---------- eventos ----------

$('#settings-btn').addEventListener('click', openSettings);
$('#cancel-btn').addEventListener('click', loadDevices);

$('#link-input').addEventListener('input', (e) => {
  const parsed = parseSetupLink(e.target.value);
  if (parsed) {
    $('#relay-input').value = parsed.relay;
    $('#token-input').value = parsed.token;
  }
});

$('#settings-form').addEventListener('submit', (e) => {
  e.preventDefault();
  saveSettings({ relay: cleanRelay($('#relay-input').value), token: $('#token-input').value.trim() });
  loadDevices();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !views.devices.hidden) refreshStatus();
});

// ---------- arranque ----------

function start() {
  const fromLink = parseSetupLink(location.href);
  if (fromLink) {
    saveSettings(fromLink);
    // Quita el token de la barra de direcciones y del historial.
    history.replaceState(null, '', location.pathname + location.search);
  }
  if (loadSettings()) loadDevices();
  else openSettings();
}

window.addEventListener('hashchange', start);

(function init() {
  start();

  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();
