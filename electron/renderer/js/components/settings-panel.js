/**
 * settings-panel.js – Settings sidebar panel.
 */
const SettingsPanel = (() => {
  let _settings = {};

  function init() {
    AppState.on('view-changed', view => {
      if (view === 'settings') _render();
    });
  }

  async function load() {
    try {
      const ws = AppState.workspacePath;
      if (!ws) return;
      const path = ws + '/.dbanalyzer/settings.json';
      const exists = await API.fsExists(path);
      if (exists) {
        _settings = JSON.parse(await API.readFile(path));
      }
    } catch { _settings = {}; }
  }

  async function save() {
    const ws = AppState.workspacePath;
    if (!ws) return;
    await API.ensureDir(ws + '/.dbanalyzer');
    await API.writeFile(ws + '/.dbanalyzer/settings.json', JSON.stringify(_settings, null, 2));
  }

  function get(key, def) { return _settings[key] ?? def; }
  function set(key, val) { _settings[key] = val; }

  function _render() {
    const container = document.getElementById('settings-content');
    container.innerHTML = '';

    // GitHub section
    const ghSection = _section(I18n.t('settings.github'));
    ghSection.appendChild(_row(I18n.t('settings.username'), 'github_username', _settings.github_username || '', 'text'));
    ghSection.appendChild(_row(I18n.t('settings.token'), 'github_token', _settings.github_token || '', 'password'));
    container.appendChild(ghSection);

    // Editor section
    const edSection = _section(I18n.t('settings.editor'));
    edSection.appendChild(_row(I18n.t('settings.fontSize'), 'editor_font_size', _settings.editor_font_size || '13', 'number'));
    edSection.appendChild(_row(I18n.t('settings.tabSize'), 'editor_tab_size', _settings.editor_tab_size || '2', 'number'));
    edSection.appendChild(_selectRow(I18n.t('settings.wordWrap'), 'editor_word_wrap', _settings.editor_word_wrap || 'on', [
      { value: 'on', label: I18n.t('settings.on') },
      { value: 'off', label: I18n.t('settings.off') },
    ]));
    // SQL Dialect
    const dialectOptions = SqlCompletion.SUPPORTED_DIALECTS.map(d => ({ value: d, label: d.charAt(0).toUpperCase() + d.slice(1) }));
    edSection.appendChild(_selectRow(I18n.t('settings.sqlDialect'), 'sql_dialect', _settings.sql_dialect || 'mysql', dialectOptions));
    container.appendChild(edSection);

    // UI section
    const uiSection = _section(I18n.t('settings.ui'));
    // Build language options from I18n supported locales
    const langOptions = Object.entries(I18n.SUPPORTED_LOCALES).map(([value, label]) => ({ value, label }));
    uiSection.appendChild(_selectRow(I18n.t('settings.language'), 'ui_language', _settings.ui_language || 'zh-CN', langOptions));
    uiSection.appendChild(_selectRow(I18n.t('settings.theme'), 'ui_theme', _settings.ui_theme || 'dark', [
      { value: 'dark', label: I18n.t('settings.themeDark') },
    ]));
    container.appendChild(uiSection);

    // Workspace
    const wsSection = _section(I18n.t('settings.workspaceSection'));
    const wsRow = document.createElement('div');
    wsRow.className = 'settings-row';
    wsRow.innerHTML = `<span class="settings-label">${I18n.t('settings.currentWorkspace')}</span><span style="font-size:12px;color:var(--fg);word-break:break-all">${AppState.workspacePath || '—'}</span>`;
    wsSection.appendChild(wsRow);
    const swBtn = document.createElement('button');
    swBtn.className = 'btn btn-sm btn-secondary';
    swBtn.textContent = I18n.t('settings.switchWorkspace');
    swBtn.style.marginTop = '8px';
    swBtn.addEventListener('click', () => App.switchWorkspace());
    wsSection.appendChild(swBtn);
    container.appendChild(wsSection);

    // Save button
    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-primary';
    saveBtn.textContent = I18n.t('settings.save');
    saveBtn.style.marginTop = '16px';
    saveBtn.addEventListener('click', async () => {
      const prevLang = _settings.ui_language;
      const prevDialect = _settings.sql_dialect;
      _collectValues();
      await save();
      StatusBar.setInfo(I18n.t('settings.saved'));

      // If language changed, reload i18n and re-apply
      if (_settings.ui_language !== prevLang) {
        await I18n.init(_settings.ui_language);
        I18n.applyToDOM();
        _render(); // Re-render settings with new language
      }

      // If SQL dialect changed, update completion provider
      if (_settings.sql_dialect !== prevDialect) {
        SqlCompletion.setDialect(_settings.sql_dialect);
      }
    });
    container.appendChild(saveBtn);
  }

  function _collectValues() {
    const inputs = document.querySelectorAll('#settings-content [data-key]');
    inputs.forEach(el => {
      _settings[el.dataset.key] = el.value;
    });
  }

  function _section(title) {
    const div = document.createElement('div');
    div.className = 'settings-section';
    const h = document.createElement('div');
    h.className = 'settings-section-title';
    h.textContent = title;
    div.appendChild(h);
    return div;
  }

  function _row(label, key, value, type) {
    const div = document.createElement('div');
    div.className = 'settings-row';
    div.innerHTML = `<span class="settings-label">${label}</span>`;
    const input = document.createElement('input');
    input.className = 'settings-input';
    input.type = type;
    input.value = value;
    input.dataset.key = key;
    div.appendChild(input);
    return div;
  }

  function _selectRow(label, key, value, options) {
    const div = document.createElement('div');
    div.className = 'settings-row';
    div.innerHTML = `<span class="settings-label">${label}</span>`;
    const sel = document.createElement('select');
    sel.className = 'settings-select';
    sel.dataset.key = key;
    for (const o of options) {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      if (o.value === value) opt.selected = true;
      sel.appendChild(opt);
    }
    div.appendChild(sel);
    return div;
  }

  return { init, load, save, get, set };
})();
