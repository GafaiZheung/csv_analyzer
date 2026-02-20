/**
 * status-bar.js – Bottom status bar.
 */
const StatusBar = (() => {
  const bar  = () => document.getElementById('status-bar');
  const conn = () => document.getElementById('status-connection');
  const info = () => document.getElementById('status-info');
  const rows = () => document.getElementById('status-rows');
  const time = () => document.getElementById('status-time');
  const ws   = () => document.getElementById('status-workspace');
  const br   = () => document.getElementById('status-branch');

  function init() {
    ws().addEventListener('click', () => App.switchWorkspace());
  }

  function setWorkspace(name) {
    ws().innerHTML = Icons.get('folder-sm') + ' ' + (name || '');
    ws().title = AppState.workspacePath || '';
  }

  function setBranch(name) { br().innerHTML = name ? Icons.get('branch') + ' ' + name : ''; }

  function setConnection(name) { conn().textContent = name; bar().classList.remove('disconnected'); }
  function setDisconnected()   { conn().textContent = I18n.t('connection.notConnected'); bar().classList.add('disconnected'); }

  function setInfo(text) { info().textContent = text; }
  function setRows(n)    { rows().textContent = n != null ? I18n.t('pagination.rows', n.toLocaleString()) : ''; }
  function setTime(ms)   { time().textContent = ms != null ? `${ms.toFixed(0)} ms` : ''; }

  function showLoading() {
    const el = document.getElementById('status-loading');
    if (el) el.classList.remove('hidden');
  }
  function hideLoading() {
    const el = document.getElementById('status-loading');
    if (el) el.classList.add('hidden');
  }

  return { init, setWorkspace, setBranch, setConnection, setDisconnected, setInfo, setRows, setTime, showLoading, hideLoading };
})();
