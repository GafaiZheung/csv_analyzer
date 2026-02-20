/**
 * tab-manager.js – Dual-panel tab system (upper: editors, lower: results).
 *
 * Upper tabs: SQL editors, table data viewers.
 * Lower tabs: Query result sets (shown on demand).
 */
const TabManager = (() => {
  const upperBar     = () => document.getElementById('upper-tab-bar');
  const upperContent = () => document.getElementById('upper-content');
  const lowerBar     = () => document.getElementById('lower-tab-bar');
  const lowerContent = () => document.getElementById('lower-content');
  const lowerPanel   = () => document.getElementById('lower-panel');
  const hSplitter    = () => document.getElementById('h-splitter');

  let _sqlCount = 0;

  function init() {
    _initHSplitter();
  }

  /* ══════════════ Upper Tabs (SQL / Table) ══════════════ */

  /**
   * Add an upper tab.
   * @param {{ type:'sql'|'table', title:string, connId:string, filePath?:string, content?:string }} opts
   * @returns {object} tab info
   */
  function addUpperTab(opts) {
    const id = AppState.nextTabId();

    // Tab header
    const tab = _makeTabEl(id, opts.type === 'table' ? 'table' : 'file-sql', opts.title, () => activateUpperTab(id), () => closeUpperTab(id));
    upperBar().appendChild(tab);

    // Pane
    const pane = document.createElement('div');
    pane.className = 'editor-pane';
    pane.dataset.tabId = id;

    if (opts.type === 'sql') {
      pane.classList.add('sql-pane');
      pane.innerHTML = `
        <div class="editor-toolbar">
          <select class="conn-select"></select>
          <button class="btn btn-run btn-sm" data-action="run">${Icons.get('play')} ${I18n.t('editor.run')}</button>
        </div>
        <div class="monaco-container"></div>
      `;
    } else {
      // Table view: data grid + analysis sidebar
      pane.classList.add('table-pane');
      pane.innerHTML = `
        <div class="table-data-area">
          <div class="editor-toolbar">
            <span class="conn-label">${_esc(_connLabel(opts.connId))}</span>
            <span class="conn-label" style="margin-left:auto;margin-right:0">${_esc(opts.title)}</span>
          </div>
          <div class="result-table-wrap"></div>
          <div class="result-footer hidden">
            <span class="result-summary"></span>
            <div class="pagination">
              <button class="btn btn-sm btn-secondary" data-page="prev">${I18n.t('pagination.prev')}</button>
              <span class="page-info"></span>
              <button class="btn btn-sm btn-secondary" data-page="next">${I18n.t('pagination.next')}</button>
            </div>
          </div>
        </div>
        <div class="v-splitter-h"></div>
        <div class="analysis-sidebar">
          <div class="analysis-tab-bar">
            <div class="analysis-tab active" data-atab="overview">${I18n.t('analysis.overview')}</div>
            <div class="analysis-tab" data-atab="stats">${I18n.t('analysis.stats')}</div>
            <div class="analysis-tab" data-atab="cell">${I18n.t('analysis.cell')}</div>
            <div class="analysis-tab" data-atab="calc">${I18n.t('analysis.calc')}</div>
          </div>
          <div class="analysis-body">
            <div class="empty-hint">${I18n.t('editor.clickColumn')}</div>
          </div>
        </div>
      `;
    }

    upperContent().appendChild(pane);

    const info = {
      id, type: opts.type, title: opts.title, connId: opts.connId,
      pane, editor: null,
      filePath: opts.filePath || null,
      dirty: false,
      lastSQL: '', lastConn: opts.connId, offset: 0, total: 0,
      _columns: null, _rows: null,
      _activeAnalysisTab: 'overview',
    };
    AppState.upperTabs.push(info);

    // Wire events
    if (opts.type === 'sql') {
      pane.querySelector('[data-action="run"]').addEventListener('click', () => {
        const sql = info.editor ? info.editor.getValue() : '';
        if (sql.trim()) App.executeSQL(info, info.connId, sql);
      });

      // Populate connection dropdown and wire switch handler
      const sel = pane.querySelector('.conn-select');
      _populateConnSelect(sel, opts.connId);
      if (!info.connId && AppState.connections.size) {
        info.connId = AppState.connections.keys().next().value;
        sel.value = info.connId;
      }
      sel.addEventListener('change', () => {
        info.connId = sel.value;
        AppState.activeConn = sel.value;
        const c = AppState.connections.get(sel.value);
        if (c) StatusBar.setConnection(c.name);
      });

      activateUpperTab(id);
      _createEditor(info, opts.content || '');
    } else {
      // Analysis tabs switching
      pane.querySelectorAll('.analysis-tab').forEach(t => {
        t.addEventListener('click', () => _switchAnalysisTab(info, t.dataset.atab));
      });
      // Analysis splitter
      _initAnalysisSplitter(pane);
      // Pagination
      pane.querySelector('[data-page="prev"]')?.addEventListener('click', () => App.executeTablePage(info, Math.max(0, info.offset - 500)));
      pane.querySelector('[data-page="next"]')?.addEventListener('click', () => App.executeTablePage(info, info.offset + 500));

      activateUpperTab(id);
    }

    _hideWelcome();
    return info;
  }

  function activateUpperTab(id) {
    upperBar().querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    upperContent().querySelectorAll('.editor-pane').forEach(p => p.classList.remove('active'));

    const tab  = upperBar().querySelector(`[data-tab-id="${id}"]`);
    const pane = upperContent().querySelector(`.editor-pane[data-tab-id="${id}"]`);
    if (tab)  tab.classList.add('active');
    if (pane) pane.classList.add('active');

    AppState.activeUpperTabId = id;
    const info = AppState.upperTabs.find(t => t.id === id);
    if (info?.editor) setTimeout(() => info.editor.layout(), 20);
  }

  function closeUpperTab(id) {
    const idx = AppState.upperTabs.findIndex(t => t.id === id);
    if (idx === -1) return;
    const info = AppState.upperTabs[idx];

    // Prompt if dirty (unsaved changes)
    if (info.dirty) {
      if (!confirm(I18n.t('editor.unsavedClose'))) return;
    }

    if (info.editor) info.editor.dispose();
    info.pane.remove();
    upperBar().querySelector(`[data-tab-id="${id}"]`)?.remove();
    AppState.upperTabs.splice(idx, 1);

    if (AppState.upperTabs.length) {
      activateUpperTab(AppState.upperTabs[Math.min(idx, AppState.upperTabs.length - 1)].id);
    } else {
      AppState.activeUpperTabId = null;
      _showWelcome();
    }
  }

  /* ══════════════ Lower Tabs (Results) ══════════════ */

  function addLowerTab(title) {
    const id = AppState.nextTabId();

    // Show lower panel
    lowerPanel().classList.remove('hidden');
    hSplitter().classList.remove('hidden');

    const tab = _makeTabEl(id, 'chart', title, () => activateLowerTab(id), () => closeLowerTab(id));
    lowerBar().appendChild(tab);

    const pane = document.createElement('div');
    pane.className = 'editor-pane result-pane';
    pane.dataset.tabId = id;
    pane.innerHTML = `
      <div class="result-table-wrap"></div>
      <div class="result-footer hidden">
        <span class="result-summary"></span>
        <div class="pagination">
          <button class="btn btn-sm btn-secondary" data-page="prev">${Icons.get('play')} ${I18n.t('pagination.prev')}</button>
          <span class="page-info"></span>
          <button class="btn btn-sm btn-secondary" data-page="next">${I18n.t('pagination.next')} ${Icons.get('play')}</button>
        </div>
      </div>
    `;
    lowerContent().appendChild(pane);

    const info = { id, title, pane, offset: 0, total: 0, lastSQL: '', lastConn: '', _columns: null, _rows: null };
    AppState.lowerTabs.push(info);

    pane.querySelector('[data-page="prev"]').addEventListener('click', () => App.executePage(info, Math.max(0, info.offset - 500)));
    pane.querySelector('[data-page="next"]').addEventListener('click', () => App.executePage(info, info.offset + 500));

    activateLowerTab(id);
    return info;
  }

  function activateLowerTab(id) {
    lowerBar().querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    lowerContent().querySelectorAll('.editor-pane').forEach(p => p.classList.remove('active'));
    lowerBar().querySelector(`[data-tab-id="${id}"]`)?.classList.add('active');
    lowerContent().querySelector(`.editor-pane[data-tab-id="${id}"]`)?.classList.add('active');
    AppState.activeLowerTabId = id;
  }

  function closeLowerTab(id) {
    const idx = AppState.lowerTabs.findIndex(t => t.id === id);
    if (idx === -1) return;
    AppState.lowerTabs[idx].pane.remove();
    lowerBar().querySelector(`[data-tab-id="${id}"]`)?.remove();
    AppState.lowerTabs.splice(idx, 1);

    if (AppState.lowerTabs.length) {
      activateLowerTab(AppState.lowerTabs[Math.min(idx, AppState.lowerTabs.length - 1)].id);
    } else {
      AppState.activeLowerTabId = null;
      lowerPanel().classList.add('hidden');
      hSplitter().classList.add('hidden');
    }
  }

  /* ══════════════ Queries ══════════════ */

  function getActiveUpper() { return AppState.upperTabs.find(t => t.id === AppState.activeUpperTabId) || null; }
  function nextSQLTitle()   { return `SQL ${++_sqlCount}`; }

  function closeActiveUpper() {
    if (AppState.activeUpperTabId) closeUpperTab(AppState.activeUpperTabId);
  }

  function findUpperByPath(filePath) {
    return AppState.upperTabs.find(t => t.filePath === filePath) || null;
  }

  /* ══════════════ Monaco Editor ══════════════ */

  function _createEditor(info, initialValue) {
    if (!window.monacoReady) {
      window.addEventListener('monaco-ready', () => _createEditor(info, initialValue), { once: true });
      return;
    }
    const container = info.pane.querySelector('.monaco-container');
    info.editor = monaco.editor.create(container, {
      value: initialValue,
      language: 'sql',
      theme: 'vs-dark',
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 13,
      fontFamily: '"SF Mono","Fira Code","Cascadia Code",Menlo,Monaco,monospace',
      lineNumbers: 'on',
      renderLineHighlight: 'line',
      padding: { top: 8, bottom: 8 },
      automaticLayout: true,
      wordWrap: 'on',
      tabSize: 2,
      scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
    });

    // Cmd+Enter to run
    info.editor.addAction({
      id: 'run-sql', label: 'Run SQL',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
      run: () => {
        const sql = info.editor.getValue();
        if (sql.trim()) App.executeSQL(info, info.connId, sql);
      },
    });

    // Cmd+S to save
    info.editor.addAction({
      id: 'save-file', label: 'Save File',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
      run: () => App.saveSqlFile(info),
    });

    // Mark dirty
    info.editor.onDidChangeModelContent(() => {
      if (!info.dirty) {
        info.dirty = true;
        const tabEl = upperBar().querySelector(`[data-tab-id="${info.id}"] .tab-label`);
        if (tabEl) tabEl.textContent = '● ' + info.title;
      }
    });
  }

  /* ══════════════ Horizontal Splitter ══════════════ */

  function _initHSplitter() {
    const splitter = hSplitter();
    const upper = document.getElementById('upper-panel');
    let startY, startH;

    splitter.addEventListener('mousedown', e => {
      e.preventDefault();
      startY = e.clientY;
      startH = upper.offsetHeight;
      splitter.classList.add('dragging');

      const onMove = ev => {
        const h = Math.max(100, startH + (ev.clientY - startY));
        upper.style.flex = 'none';
        upper.style.height = h + 'px';
        // Re-layout any active editor
        const info = getActiveUpper();
        if (info?.editor) info.editor.layout();
      };
      const onUp = () => {
        splitter.classList.remove('dragging');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  /* ══════════════ Analysis Splitter ══════════════ */

  function _initAnalysisSplitter(pane) {
    const splitter  = pane.querySelector('.v-splitter-h');
    const analysis  = pane.querySelector('.analysis-sidebar');
    if (!splitter || !analysis) return;
    let startX, startW;

    splitter.addEventListener('mousedown', e => {
      e.preventDefault();
      startX = e.clientX;
      startW = analysis.offsetWidth;
      splitter.classList.add('dragging');

      const onMove = ev => {
        const w = Math.max(150, Math.min(600, startW - (ev.clientX - startX)));
        analysis.style.width = w + 'px';
      };
      const onUp = () => {
        splitter.classList.remove('dragging');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  /* ══════════════ Analysis Tabs ══════════════ */

  function _switchAnalysisTab(info, tabName) {
    info._activeAnalysisTab = tabName;
    const pane = info.pane;
    pane.querySelectorAll('.analysis-tab').forEach(t => t.classList.toggle('active', t.dataset.atab === tabName));
    App.loadAnalysisTab(info, tabName);
  }

  /* ══════════════ Shared Helpers ══════════════ */

  function _makeTabEl(id, iconName, title, onActivate, onClose) {
    const tab = document.createElement('div');
    tab.className = 'tab';
    tab.dataset.tabId = id;

    tab.appendChild(Icons.el(iconName));

    const lbl = document.createElement('span');
    lbl.className = 'tab-label'; lbl.textContent = title;

    const close = document.createElement('button');
    close.className = 'close-btn'; close.innerHTML = Icons.get('close', 12);
    close.addEventListener('click', e => { e.stopPropagation(); onClose(); });

    tab.append(lbl, close);
    tab.addEventListener('click', onActivate);
    return tab;
  }

  function _connLabel(connId) {
    const c = AppState.connections.get(connId);
    return c ? c.name : connId || '—';
  }

  function _populateConnSelect(sel, activeConnId) {
    sel.innerHTML = '';
    if (!AppState.connections.size) {
      const opt = document.createElement('option');
      opt.value = ''; opt.textContent = I18n.t('connection.notConnected');
      sel.appendChild(opt);
      return;
    }
    for (const [id, conn] of AppState.connections) {
      const opt = document.createElement('option');
      opt.value = id; opt.textContent = conn.name;
      if (id === activeConnId) opt.selected = true;
      sel.appendChild(opt);
    }
  }

  function refreshConnSelects() {
    for (const tab of AppState.upperTabs) {
      if (tab.type === 'sql') {
        const sel = tab.pane?.querySelector('.conn-select');
        if (sel) _populateConnSelect(sel, tab.connId);
      }
    }
  }

  function _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function _hideWelcome() { document.getElementById('upper-welcome')?.classList.add('hidden'); }
  function _showWelcome() { document.getElementById('upper-welcome')?.classList.remove('hidden'); }

  return {
    init,
    addUpperTab, activateUpperTab, closeUpperTab, closeActiveUpper,
    addLowerTab, activateLowerTab, closeLowerTab,
    getActiveUpper, nextSQLTitle, findUpperByPath,
    refreshConnSelects,
  };
})();
