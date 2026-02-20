/**
 * app.js – Main application controller. Wires together all components.
 */
const App = (() => {

  /* ══════════════ Bootstrap ══════════════ */

  async function init() {
    // Load i18n first
    const savedLocale = (await API.getConfig().catch(() => ({}))).locale || 'zh-CN';
    await I18n.init(savedLocale);
    I18n.applyToDOM();

    // Init components
    ActivityBar.init();
    Sidebar.init();
    ConnectionDialog.init();
    TabManager.init();
    AnalysisPanel.init();
    GitPanel.init();
    SettingsPanel.init();
    ExtensionsPanel.init();
    StatusBar.init();

    // Register lazy-expand handlers for sidebar tree
    Sidebar.onExpand({
      conn:   async (connId) => {
        try {
          StatusBar.showLoading();
          const payload = await API.getSchemas(connId);
          const schemas = payload.schemas || [];
          const conn = AppState.connections.get(connId);
          if (conn) conn.schemas = schemas;
          Sidebar.setSchemas(connId, schemas);
        } catch (err) { console.error('Expand conn failed:', err); }
        finally { StatusBar.hideLoading(); }
      },
      schema: async (connId, schema) => {
        try {
          StatusBar.showLoading();
          const tp = await API.getTables(connId, schema);
          Sidebar.setTables(connId, schema, tp.tables || []);
        } catch (err) { console.error('Expand schema failed:', err); }
        finally { StatusBar.hideLoading(); }
      },
      table:  async (connId, schema, table) => {
        try {
          StatusBar.showLoading();
          const cp = await API.getColumns(connId, schema, table);
          Sidebar.setColumns(connId, schema, table, cp.columns || []);
          // Feed column data to SQL completion
          SqlCompletion.setCachedColumns(connId, schema, table, cp.columns || []);
        } catch (err) { console.error('Expand table failed:', err); }
        finally { StatusBar.hideLoading(); }
      },
    });

    // Initialize SQL completion after Monaco is ready
    const dialectSetting = SettingsPanel.get('sql_dialect', 'mysql');
    if (window.monacoReady) {
      await SqlCompletion.init(dialectSetting);
    } else {
      window.addEventListener('monaco-ready', () => SqlCompletion.init(dialectSetting), { once: true });
    }

    _initSidebarResize();
    _initKeyboard();

    // Welcome screen
    document.getElementById('btn-select-workspace').addEventListener('click', _selectWorkspace);

    // Try to restore last workspace
    try {
      const config = await API.getConfig();
      if (config.lastWorkspace) {
        const exists = await API.fsExists(config.lastWorkspace);
        if (exists) { await _openWorkspace(config.lastWorkspace); return; }
      }
    } catch (err) { console.error('Config load failed:', err); }

    _showWelcome();
  }

  /* ══════════════ Workspace ══════════════ */

  async function _selectWorkspace() {
    const result = await API.selectFolder();
    if (result.canceled || !result.filePaths.length) return;
    await _openWorkspace(result.filePaths[0]);
  }

  async function _openWorkspace(wsPath) {
    AppState.workspacePath = wsPath;

    // Persist last workspace
    const config = await API.getConfig();
    config.lastWorkspace = wsPath;
    await API.saveConfig(config);

    // Ensure workspace metadata directory
    await API.ensureDir(wsPath + '/.dbanalyzer');

    // Switch screens
    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');

    const folderName = wsPath.split('/').pop();
    StatusBar.setWorkspace(folderName);
    StatusBar.setDisconnected();

    // Load settings, connections, scripts
    await SettingsPanel.load();

    // Apply language from settings
    const lang = SettingsPanel.get('ui_language', 'zh-CN');
    if (lang !== I18n.locale()) {
      await I18n.init(lang);
      I18n.applyToDOM();
    }
    await _loadConnections();
    await _loadCsvRecords();
    await refreshScripts();
    _checkGitBranch();

    // Auto-refresh connections periodically (every 30s)
    _startAutoRefresh();
  }

  let _autoRefreshTimer = null;
  function _startAutoRefresh() {
    if (_autoRefreshTimer) clearInterval(_autoRefreshTimer);
    _autoRefreshTimer = setInterval(async () => {
      for (const [connId] of AppState.connections) {
        try { await refreshConnection(connId); } catch {}
      }
    }, 30000);
  }

  async function switchWorkspace() {
    const result = await API.selectFolder();
    if (result.canceled || !result.filePaths.length) return;

    // Tear down current workspace
    while (AppState.upperTabs.length) TabManager.closeUpperTab(AppState.upperTabs[0].id);
    while (AppState.lowerTabs.length) TabManager.closeLowerTab(AppState.lowerTabs[0].id);
    for (const [id] of AppState.connections) {
      try { await API.disconnect(id); } catch {}
      Sidebar.removeConnection(id);
    }
    AppState.connections.clear();
    AppState.activeConn = '';

    await _openWorkspace(result.filePaths[0]);
  }

  /* ══════════════ Connections ══════════════ */

  async function _loadConnections() {
    try {
      const p = AppState.workspacePath + '/.dbanalyzer/connections.json';
      if (!(await API.fsExists(p))) return;
      const data = JSON.parse(await API.readFile(p));
      if (!Array.isArray(data)) return;
      for (const cfg of data) await createConnection(cfg.conn_id, cfg, true);
    } catch (err) { console.error('Load connections:', err); }
  }

  async function _saveConnections() {
    const list = [];
    for (const [, c] of AppState.connections) list.push(c.config);
    await API.ensureDir(AppState.workspacePath + '/.dbanalyzer');
    await API.writeFile(AppState.workspacePath + '/.dbanalyzer/connections.json', JSON.stringify(list, null, 2));
  }

  async function createConnection(connId, config, silent = false) {
    try {
      if (!silent) { StatusBar.setInfo(I18n.t('connection.connecting')); StatusBar.showLoading(); }
      const payload = await API.connect(config);

      // For CSV connections, use CSV filename as display name
      let name = config.name || config.db_type || connId;
      if (config._csvPaths && config._csvPaths.length) {
        const csvNames = config._csvPaths.map(p => p.split('/').pop());
        name = csvNames.join(', ');
      }

      AppState.connections.set(connId, { name, dbType: config.db_type, config, schemas: payload.schemas || [], csvPaths: config._csvPaths || [] });
      AppState.activeConn = connId;

      Sidebar.addConnection(connId, name, config.db_type);
      StatusBar.setConnection(name);
      StatusBar.setInfo(I18n.t('connection.connected'));

      // Store schemas but don't auto-expand (lazy loaded on expand click)
      // Just set schemas so they're available when user clicks to expand
      if (payload.schemas?.length) {
        // Schemas are loaded lazily when user expands the connection node
      }

      // If there are CSV paths to load, load them
      if (config._csvPaths && config._csvPaths.length) {
        const csvTableNames = [];
        for (const csvPath of config._csvPaths) {
          try {
            const csvRes = await API.loadCSV(connId, csvPath);
            if (csvRes.table_name) csvTableNames.push(csvRes.table_name);
          } catch (err) {
            if (!silent) console.error('CSV load failed:', csvPath, err);
          }
        }

        // For CSV connections: show only the imported tables (skip DuckDB internal tables)
        // and directly expand columns
        Sidebar.removeConnection(connId);
        Sidebar.addConnection(connId, name, 'csv');

        const schema = 'main';
        try {
          const tp = await API.getTables(connId, schema);
          const allTables = tp.tables || [];
          // Filter to only CSV-imported tables (skip system tables like information_schema entries)
          const userTables = allTables.filter(t => csvTableNames.includes(t.name));
          Sidebar.setSchemas(connId, [schema]);
          Sidebar.setTables(connId, schema, userTables);

          // Auto-expand: load and show columns for each CSV table
          for (const t of userTables) {
            try {
              const cp = await API.getColumns(connId, schema, t.name);
              Sidebar.setColumns(connId, schema, t.name, cp.columns || []);
              Sidebar.expandPath(connId, schema, t.name);
            } catch {}
          }
        } catch {}
      }

      if (!silent) await _saveConnections();
      TabManager.refreshConnSelects();
    } catch (err) {
      if (!silent) { StatusBar.setInfo(I18n.t('connection.connFailed')); alert(I18n.t('connection.connFailed') + ': ' + err.message); }
      else console.error('Auto-connect failed:', err);
    } finally {
      StatusBar.hideLoading();
    }
  }

  async function refreshConnection(connId) {
    try {
      const payload = await API.getSchemas(connId);
      const schemas = payload.schemas || [];
      const conn = AppState.connections.get(connId);
      if (conn) conn.schemas = schemas;
      Sidebar.setSchemas(connId, schemas);
    } catch (err) { StatusBar.setInfo(I18n.t('connection.refreshFailed')); }
  }

  async function _loadTables(connId, schema) {
    try {
      const tp = await API.getTables(connId, schema);
      Sidebar.setTables(connId, schema, tp.tables || []);
    } catch {}
  }

  async function disconnect(connId) {
    try { await API.disconnect(connId); } catch {}
    AppState.connections.delete(connId);
    Sidebar.removeConnection(connId);

    if (AppState.activeConn === connId) {
      const next = AppState.connections.keys().next().value;
      if (next) { AppState.activeConn = next; StatusBar.setConnection(AppState.connections.get(next).name); }
      else { AppState.activeConn = ''; StatusBar.setDisconnected(); }
    }
    await _saveConnections();
    TabManager.refreshConnSelects();
  }

  /* ══════════════ SQL Scripts ══════════════ */

  async function refreshScripts() {
    if (!AppState.workspacePath) return;
    const entries = await API.readDir(AppState.workspacePath);
    const files = entries.filter(e => !e.isDir && e.name.endsWith('.sql')).map(e => e.name).sort();
    Sidebar.refreshScripts(files);
  }

  async function newSqlFile() {
    if (!AppState.workspacePath) {
      alert(I18n.t('git.selectWorkspace'));
      return;
    }
    // Auto-generate filename with timestamp (no prompt – Electron doesn't support window.prompt)
    const ts = new Date();
    const pad = n => String(n).padStart(2, '0');
    const defaultName = `query_${ts.getFullYear()}${pad(ts.getMonth()+1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.sql`;
    await API.writeFile(AppState.workspacePath + '/' + defaultName, '-- ' + defaultName + '\n');
    await refreshScripts();
    await openSqlFile(defaultName);
  }

  function newSqlTab(connId) {
    connId = connId || AppState.activeConn;
    if (!connId) { alert(I18n.t('connection.createConn')); return; }
    TabManager.addUpperTab({ type: 'sql', title: TabManager.nextSQLTitle(), connId });
  }

  async function openSqlFile(filename) {
    const fp = AppState.workspacePath + '/' + filename;
    const existing = TabManager.findUpperByPath(fp);
    if (existing) { TabManager.activateUpperTab(existing.id); return; }
    const content = await API.readFile(fp);
    TabManager.addUpperTab({ type: 'sql', title: filename, connId: AppState.activeConn || '', filePath: fp, content });
  }

  async function saveSqlFile(info) {
    if (!info || info.type !== 'sql') return;
    let fp = info.filePath;
    if (!fp) {
      // Auto-generate a filename for untitled tabs
      const ts = new Date();
      const pad = n => String(n).padStart(2, '0');
      const fn = `query_${ts.getFullYear()}${pad(ts.getMonth()+1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.sql`;
      fp = AppState.workspacePath + '/' + fn;
      info.filePath = fp;
      info.title = fn;
    }
    await API.writeFile(fp, info.editor ? info.editor.getValue() : '');
    info.dirty = false;
    const lbl = document.querySelector(`[data-tab-id="${info.id}"] .tab-label`);
    if (lbl) lbl.textContent = info.title;
    StatusBar.setInfo(I18n.t('editor.saved'));
    await refreshScripts();
  }

  async function deleteSqlFile(filename) {
    await API.deleteFile(AppState.workspacePath + '/' + filename);
    const tab = TabManager.findUpperByPath(AppState.workspacePath + '/' + filename);
    if (tab) TabManager.closeUpperTab(tab.id);
    await refreshScripts();
  }

  /* ══════════════ SQL Execution ══════════════ */

  async function executeSQL(info, connId, sql) {
    if (!connId) { alert(I18n.t('connection.selectConn')); return; }
    StatusBar.setInfo(I18n.t('editor.executing'));
    StatusBar.showLoading();
    const t0 = performance.now();
    try {
      const payload = await API.executeSQL(connId, sql);
      const elapsed = performance.now() - t0;
      info.lastSQL = sql;
      info.lastConn = connId;

      if (payload.columns && payload.rows) {
        const total = payload.row_count || payload.total || payload.rows.length;
        const tab = TabManager.addLowerTab(I18n.t('editor.resultPrefix') + ': ' + (info.title || 'SQL'));
        tab.lastSQL = sql; tab.lastConn = connId;
        ResultTable.setResult(tab, payload.columns, payload.rows, total, elapsed, 0);
        StatusBar.setRows(total);
      } else {
        const tab = TabManager.addLowerTab(I18n.t('editor.message'));
        ResultTable.setMessage(tab, payload.message || I18n.t('editor.executed'), elapsed);
      }
      StatusBar.setTime(elapsed);
      StatusBar.setInfo(I18n.t('editor.executed'));
    } catch (err) {
      const elapsed = performance.now() - t0;
      const tab = TabManager.addLowerTab(I18n.t('editor.error'));
      ResultTable.setError(tab, err.message);
      StatusBar.setInfo(I18n.t('editor.execFailed'));
      StatusBar.setTime(elapsed);
    } finally {
      StatusBar.hideLoading();
    }
  }

  async function executePage(info, offset) {
    if (!info.lastSQL || !info.lastConn) return;
    try {
      const p = await API.executeSQL(info.lastConn, info.lastSQL, 500, offset);
      const total = p.row_count || p.total || p.rows.length;
      ResultTable.setResult(info, p.columns, p.rows, total, 0, offset);
    } catch (err) { ResultTable.setError(info, err.message); }
  }

  /* ══════════════ Table Viewing ══════════════ */

  async function openTable(connId, schema, tableName) {
    const key = `${connId}:${schema}.${tableName}`;
    const existing = AppState.upperTabs.find(t => t.type === 'table' && t._tableKey === key);
    if (existing) { TabManager.activateUpperTab(existing.id); return; }

    const tab = TabManager.addUpperTab({ type: 'table', title: tableName, connId });
    tab._tableKey = key;
    tab._schema = schema;
    tab._tableName = tableName;
    await _loadTableData(tab, 0);
    loadAnalysisTab(tab, 'overview');
  }

  /** Return the correct quote character for the given db type */
  function _quoteId(dbType) {
    const backtickTypes = ['mysql', 'mariadb', 'starrocks', 'doris'];
    return backtickTypes.includes(dbType) ? '`' : '"';
  }

  async function _loadTableData(tab, offset) {
    const conn = AppState.connections.get(tab.connId);
    const q = _quoteId(conn?.dbType);
    // Don't bake LIMIT/OFFSET into the SQL – let the backend handle pagination
    const sql = `SELECT * FROM ${q}${tab._schema}${q}.${q}${tab._tableName}${q}`;
    StatusBar.showLoading();
    try {
      const p = await API.executeSQL(tab.connId, sql, 500, offset);
      tab.lastSQL = sql; tab.lastConn = tab.connId;
      tab.offset = offset; tab.total = p.row_count || p.total || p.rows.length;
      tab._columns = p.columns; tab._rows = p.rows;
      ResultTable.setResult(tab, p.columns, p.rows, tab.total, 0, offset);
      StatusBar.setRows(tab.total);
    } catch (err) { ResultTable.setError(tab, err.message); }
    finally { StatusBar.hideLoading(); }
  }

  async function executeTablePage(info, offset) { await _loadTableData(info, offset); }

  /* ══════════════ Analysis ══════════════ */

  async function analyzeColumn(info, colName, values) {
    info._activeAnalysisTab = 'stats';
    info.pane?.querySelectorAll('.analysis-tab').forEach(t => t.classList.toggle('active', t.dataset.atab === 'stats'));
    try {
      const data = await API.columnStats(colName, values);
      AnalysisPanel.showColumnStats(info, data);
    } catch (err) {
      const body = info.pane?.querySelector('.analysis-body');
      if (body) body.innerHTML = `<div class="result-message error">${err.message}</div>`;
    }
  }

  async function loadAnalysisTab(info, tabName) {
    if (!info._columns || !info._rows) {
      const body = info.pane?.querySelector('.analysis-body');
      if (body) body.innerHTML = `<div class="empty-hint">${I18n.t('editor.noData')}</div>`;
      return;
    }
    try {
      switch (tabName) {
        case 'overview': {
          const d = await API.dataProfile(info._columns, info._rows);
          AnalysisPanel.showOverview(info, d);
          break;
        }
        case 'stats': {
          const d = await API.missingValues(info._columns, info._rows);
          AnalysisPanel.showMissing(info, d);
          break;
        }
        case 'cell':
          AnalysisPanel.showCellInfo(info, '—', '选择一个单元格查看详情');
          break;
        case 'calc': {
          const d = await API.correlation(info._columns, info._rows);
          AnalysisPanel.showCorrelation(info, d);
          break;
        }
      }
    } catch (err) {
      const body = info.pane?.querySelector('.analysis-body');
      if (body) body.innerHTML = `<div class="result-message error">${err.message}</div>`;
    }
  }

  /* ══════════════ CSV Import ══════════════ */

  async function openCSV() {
    const result = await API.openFileDialog();
    if (result.canceled || !result.filePaths.length) return;
    const csvPath = result.filePaths[0];
    const csvFileName = csvPath.split('/').pop();

    // Find an existing DuckDB connection or create a new one
    let connId = AppState.activeConn;
    let conn = connId ? AppState.connections.get(connId) : null;

    // Only reuse active connection if it's DuckDB (CSV loading requires DuckDB driver)
    if (!conn || conn.dbType !== 'duckdb') {
      // Try to find any existing DuckDB connection
      connId = null;
      for (const [id, c] of AppState.connections) {
        if (c.dbType === 'duckdb') { connId = id; conn = c; break; }
      }
    }

    if (!connId) {
      // Create a new DuckDB connection for CSV
      connId = 'csv_' + Date.now();
      const config = {
        conn_id: connId,
        db_type: 'duckdb',
        name: csvFileName,
        _csvPaths: [csvPath],
      };
      await createConnection(connId, config);
      await _saveCsvRecords(connId, csvPath);
      return;
    }

    // Load CSV into existing DuckDB connection
    try {
      StatusBar.setInfo(I18n.t('csv.importing'));
      StatusBar.showLoading();
      const p = await API.loadCSV(connId, csvPath);
      StatusBar.setInfo(I18n.t('csv.imported') + ': ' + (p.table_name || ''));

      // Update the connection's CSV paths
      if (!conn.csvPaths) conn.csvPaths = [];
      if (!conn.csvPaths.includes(csvPath)) conn.csvPaths.push(csvPath);
      if (!conn.config._csvPaths) conn.config._csvPaths = [];
      if (!conn.config._csvPaths.includes(csvPath)) conn.config._csvPaths.push(csvPath);

      // Update display name to show CSV filenames
      const csvNames = conn.csvPaths.map(p => p.split('/').pop());
      conn.name = csvNames.join(', ');
      Sidebar.removeConnection(connId);
      Sidebar.addConnection(connId, conn.name, 'csv');

      await refreshConnection(connId);
      await _saveConnections();
      await _saveCsvRecords(connId, csvPath);

      if (p.table_name) {
        const schemas = conn.schemas || ['main'];
        await openTable(connId, schemas[0], p.table_name);
      }
    } catch (err) { alert(I18n.t('csv.importFailed') + ': ' + err.message); StatusBar.setInfo(I18n.t('csv.failed')); }
    finally { StatusBar.hideLoading(); }
  }

  /** Save CSV file paths for auto-reload on next launch */
  async function _saveCsvRecords(connId, csvPath) {
    const ws = AppState.workspacePath;
    if (!ws) return;
    try {
      await API.ensureDir(ws + '/.dbanalyzer');
      const recordPath = ws + '/.dbanalyzer/csv_records.json';
      let records = {};
      try {
        if (await API.fsExists(recordPath)) {
          records = JSON.parse(await API.readFile(recordPath));
        }
      } catch {}
      if (!records[connId]) records[connId] = [];
      if (!records[connId].includes(csvPath)) records[connId].push(csvPath);
      await API.writeFile(recordPath, JSON.stringify(records, null, 2));
    } catch (err) { console.error('Save CSV records failed:', err); }
  }

  /** Load saved CSV records and auto-reconnect */
  async function _loadCsvRecords() {
    const ws = AppState.workspacePath;
    if (!ws) return;
    try {
      const recordPath = ws + '/.dbanalyzer/csv_records.json';
      if (!(await API.fsExists(recordPath))) return;
      const records = JSON.parse(await API.readFile(recordPath));
      for (const [connId, paths] of Object.entries(records)) {
        if (AppState.connections.has(connId)) continue;
        // Validate paths still exist
        const validPaths = [];
        for (const p of paths) {
          if (await API.fsExists(p)) validPaths.push(p);
        }
        if (validPaths.length === 0) continue;

        const csvNames = validPaths.map(p => p.split('/').pop());
        const config = {
          conn_id: connId,
          db_type: 'duckdb',
          name: csvNames.join(', '),
          _csvPaths: validPaths,
        };
        await createConnection(connId, config, true);
      }
    } catch (err) { console.error('Load CSV records failed:', err); }
  }

  /* ══════════════ Keyboard Shortcuts ══════════════ */

  function _initKeyboard() {
    document.addEventListener('keydown', e => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      switch (e.key.toLowerCase()) {
        case 'n': e.preventDefault(); ConnectionDialog.show(); break;
        case 'o': e.preventDefault(); openCSV(); break;
        case 't': e.preventDefault(); AppState.activeConn ? newSqlTab() : alert(I18n.t('connection.createConn')); break;
        case 'w': e.preventDefault(); TabManager.closeActiveUpper(); break;
        case 's': e.preventDefault(); { const a = TabManager.getActiveUpper(); if (a?.type === 'sql') saveSqlFile(a); } break;
      }
    });
  }

  /* ══════════════ Sidebar Resize ══════════════ */

  function _initSidebarResize() {
    const handle = document.getElementById('sidebar-resize');
    const sidebar = document.getElementById('sidebar');
    let startX, startW;

    handle.addEventListener('mousedown', e => {
      e.preventDefault();
      startX = e.clientX;
      startW = sidebar.offsetWidth;
      handle.classList.add('dragging');

      const onMove = ev => sidebar.style.width = Math.max(180, Math.min(600, startW + (ev.clientX - startX))) + 'px';
      const onUp = () => {
        handle.classList.remove('dragging');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        const a = TabManager.getActiveUpper();
        if (a?.editor) a.editor.layout();
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  /* ══════════════ Helpers ══════════════ */

  function _showWelcome() {
    document.getElementById('welcome-screen').classList.remove('hidden');
    document.getElementById('app').classList.add('hidden');
  }

  async function _checkGitBranch() {
    const ws = AppState.workspacePath;
    if (!ws) return;
    if (await API.fsExists(ws + '/.git')) {
      const res = await API.git(ws, ['branch', '--show-current']);
      if (res.ok) StatusBar.setBranch(res.stdout.trim());
    }
  }

  /* ══════════════ Public ══════════════ */

  return {
    init, switchWorkspace,
    createConnection, refreshConnection, disconnect,
    newSqlFile, newSqlTab, openSqlFile, saveSqlFile, deleteSqlFile,
    executeSQL, executePage,
    openTable, executeTablePage,
    analyzeColumn, loadAnalysisTab,
    openCSV,
  };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
