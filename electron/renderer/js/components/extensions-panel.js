/**
 * extensions-panel.js – Extensions/plugins management panel.
 *
 * Built-in extensions are always shown as "installed".
 * Database driver extensions can be installed on-demand via pip.
 */
const ExtensionsPanel = (() => {

  /* ── Extension registry ── */
  const BUILTIN = [
    { id: 'data-analysis',  nameKey: 'extensions.dataAnalysis',  descKey: 'extensions.dataAnalysisDesc', builtin: true },
    { id: 'multi-driver',   nameKey: 'extensions.multiDriver',   descKey: 'extensions.multiDriverDesc',  builtin: true },
    { id: 'csv-import',     nameKey: 'extensions.csvImport',     descKey: 'extensions.csvImportDesc',    builtin: true },
  ];

  /**
   * Each driver extension entry:
   *   id        – unique identifier
   *   nameKey   – i18n key for display name
   *   descKey   – i18n key for description
   *   pipPkg    – pip package(s) to install
   *   importPkg – Python import name used to check if installed
   *   dbType    – the db_type string registered in DRIVER_REGISTRY
   *   port      – default port
   */
  const DB_DRIVERS = [
    {
      id: 'driver-starrocks', nameKey: 'extensions.starrocks', descKey: 'extensions.starrocksDesc',
      pipPkg: ['starrocks'], importPkg: 'starrocks', dbType: 'starrocks', port: 9030,
    },
    {
      id: 'driver-doris', nameKey: 'extensions.doris', descKey: 'extensions.dorisDesc',
      pipPkg: ['pydoris'], importPkg: 'pydoris', dbType: 'doris', port: 9030,
    },
    {
      id: 'driver-clickhouse', nameKey: 'extensions.clickhouse', descKey: 'extensions.clickhouseDesc',
      pipPkg: ['clickhouse-sqlalchemy', 'clickhouse-driver'], importPkg: 'clickhouse_sqlalchemy', dbType: 'clickhouse', port: 8123,
    },
    {
      id: 'driver-mssql', nameKey: 'extensions.mssql', descKey: 'extensions.mssqlDesc',
      pipPkg: ['pyodbc'], importPkg: 'pyodbc', dbType: 'mssql', port: 1433,
    },
    {
      id: 'driver-oracle', nameKey: 'extensions.oracle', descKey: 'extensions.oracleDesc',
      pipPkg: ['cx_Oracle'], importPkg: 'cx_Oracle', dbType: 'oracle', port: 1521,
    },
    {
      id: 'driver-mariadb', nameKey: 'extensions.mariadb', descKey: 'extensions.mariadbDesc',
      pipPkg: ['pymysql'], importPkg: 'pymysql', dbType: 'mariadb', port: 3306,
    },
  ];

  const _status = new Map(); // id → 'installed' | 'not-installed' | 'installing'

  function init() {
    AppState.on('view-changed', view => {
      if (view === 'extensions') render();
    });

    // Background-check installed drivers so we can add them to the connection dialog
    _checkInstalledDrivers();
  }

  async function _checkInstalledDrivers() {
    await Promise.all(DB_DRIVERS.map(async ext => {
      try {
        const ok = await API.pipCheck(ext.importPkg);
        _status.set(ext.id, ok ? 'installed' : 'not-installed');
      } catch {
        _status.set(ext.id, 'not-installed');
      }
    }));
    addInstalledDriversToDialog();
  }

  async function render() {
    const container = document.getElementById('extensions-content');
    if (!container) return;
    container.innerHTML = '<div class="empty-hint"><div class="spinner"></div></div>';

    // Check driver availability in parallel
    await Promise.all(DB_DRIVERS.map(async ext => {
      if (_status.has(ext.id)) return; // use cached
      try {
        const ok = await API.pipCheck(ext.importPkg);
        _status.set(ext.id, ok ? 'installed' : 'not-installed');
      } catch {
        _status.set(ext.id, 'not-installed');
      }
    }));

    _renderCards(container);
  }

  function _renderCards(container) {
    container.innerHTML = '';

    // Section: Built-in
    const builtinTitle = _el('div', 'ext-section-title');
    builtinTitle.textContent = I18n.t('extensions.builtinSection');
    container.appendChild(builtinTitle);

    for (const ext of BUILTIN) {
      container.appendChild(_createCard(ext, 'installed'));
    }

    // Section: Database Drivers
    const driverTitle = _el('div', 'ext-section-title');
    driverTitle.style.marginTop = '16px';
    driverTitle.textContent = I18n.t('extensions.driverSection');
    container.appendChild(driverTitle);

    for (const ext of DB_DRIVERS) {
      const st = _status.get(ext.id) || 'not-installed';
      container.appendChild(_createCard(ext, st));
    }
  }

  function _createCard(ext, status) {
    const card = _el('div', 'ext-card');

    const header = _el('div', 'ext-card-header');

    const info = _el('div', 'ext-card-info');
    const name = _el('div', 'ext-name');
    name.textContent = I18n.t(ext.nameKey);
    const desc = _el('div', 'ext-desc');
    desc.textContent = I18n.t(ext.descKey);
    info.appendChild(name);
    info.appendChild(desc);
    header.appendChild(info);

    const action = _el('div', 'ext-card-action');
    if (status === 'installed') {
      const badge = _el('span', 'ext-badge installed');
      badge.textContent = I18n.t('extensions.installed');
      action.appendChild(badge);
    } else if (status === 'installing') {
      const badge = _el('span', 'ext-badge installing');
      badge.innerHTML = `<span class="spinner" style="width:12px;height:12px;border-width:1.5px;display:inline-block;vertical-align:middle;margin-right:4px"></span>${I18n.t('extensions.installing')}`;
      action.appendChild(badge);
    } else {
      const btn = _el('button', 'btn btn-sm btn-primary ext-install-btn');
      btn.textContent = I18n.t('extensions.install');
      btn.addEventListener('click', () => _install(ext));
      action.appendChild(btn);
    }

    header.appendChild(action);
    card.appendChild(header);

    // Show pip packages as a small hint
    if (ext.pipPkg) {
      const hint = _el('div', 'ext-pip-hint');
      hint.textContent = `pip: ${ext.pipPkg.join(', ')}`;
      card.appendChild(hint);
    }

    return card;
  }

  async function _install(ext) {
    _status.set(ext.id, 'installing');
    const container = document.getElementById('extensions-content');
    _renderCards(container);

    try {
      const res = await API.pipInstall(ext.pipPkg);
      if (res.ok) {
        _status.set(ext.id, 'installed');
        StatusBar.setInfo(`${I18n.t(ext.nameKey)} ${I18n.t('extensions.installSuccess')}`);
        // Dynamically add to connection dialog
        _addToConnectionDialog(ext);
      } else {
        _status.set(ext.id, 'not-installed');
        StatusBar.setInfo(`${I18n.t('extensions.installFailed')}: ${res.stderr.slice(0, 120)}`);
      }
    } catch (e) {
      _status.set(ext.id, 'not-installed');
      StatusBar.setInfo(`${I18n.t('extensions.installFailed')}: ${e.message}`);
    }
    _renderCards(container);
  }

  function _addToConnectionDialog(ext) {
    // Add option to the db type select if not already present
    const sel = document.getElementById('conn-db-type');
    if (!sel) return;
    for (const opt of sel.options) {
      if (opt.value === ext.dbType) return; // already there
    }
    const option = document.createElement('option');
    option.value = ext.dbType;
    option.textContent = I18n.t(ext.nameKey);
    sel.appendChild(option);
  }

  /**
   * On init, add installed driver db types to the connection dialog.
   */
  function addInstalledDriversToDialog() {
    for (const ext of DB_DRIVERS) {
      if (_status.get(ext.id) === 'installed') {
        _addToConnectionDialog(ext);
      }
    }
  }

  /** Get the list of db types for installed driver extensions */
  function getInstalledDbTypes() {
    return DB_DRIVERS.filter(e => _status.get(e.id) === 'installed').map(e => e.dbType);
  }

  function _el(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }

  return { init, render, addInstalledDriversToDialog, getInstalledDbTypes, DB_DRIVERS };
})();
