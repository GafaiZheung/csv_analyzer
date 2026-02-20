/**
 * sidebar.js – Workspace sidebar: data sources tree + SQL scripts list.
 */
const Sidebar = (() => {
  const dbTree     = () => document.getElementById('db-tree');
  const scriptTree = () => document.getElementById('script-tree');

  // Callbacks for lazy loading
  let _onExpandConn   = null;  // (connId) => Promise
  let _onExpandSchema  = null;  // (connId, schema) => Promise
  let _onExpandTable   = null;  // (connId, schema, table) => Promise

  function init() {
    document.getElementById('btn-add-conn').addEventListener('click', () => ConnectionDialog.show());
    document.getElementById('btn-refresh').addEventListener('click', _refreshActive);
    document.getElementById('btn-new-script').addEventListener('click', () => App.newSqlFile());
    document.getElementById('sidebar-filter').addEventListener('input', _onFilter);

    // Section toggle
    document.querySelectorAll('.section-header[data-toggle]').forEach(hdr => {
      hdr.addEventListener('click', e => {
        if (e.target.closest('.section-actions')) return;
        const section = hdr.closest('.sidebar-section');
        const content = section.querySelector('.section-content');
        const arrow   = hdr.querySelector('.arrow');
        const collapsed = !content.classList.contains('collapsed');
        content.classList.toggle('collapsed', collapsed);
        arrow.classList.toggle('open', !collapsed);
      });
    });
  }

  /* ══════════ Data‑source tree ══════════ */

  function addConnection(connId, name, dbType) {
    const group = _el('div', 'tree-conn', { 'data-conn': connId });
    const iconName = dbType === 'csv' ? 'file-csv' : 'database';
    const item  = _treeItem(iconName, name, 0, true);
    item.addEventListener('click', () => _lazyToggle(group, item, 'conn', { connId }));

    const disc = _ctxBtn('disconnect', I18n.t('sidebar.disconnect'), e => { e.stopPropagation(); App.disconnect(connId); });
    const plus = _ctxBtn('plus', I18n.t('sidebar.newSql'), e => { e.stopPropagation(); App.newSqlTab(connId); });
    item.append(disc, plus);

    group.appendChild(item);
    group.appendChild(_el('div', 'tree-group collapsed'));
    dbTree().appendChild(group);
  }

  function setSchemas(connId, schemas) {
    const g = _connChildren(connId); if (!g) return;
    g.innerHTML = '';
    for (const s of schemas) {
      const sg = _el('div', 'tree-schema', { 'data-schema': s });
      const si = _treeItem('folder', s, 1, true);
      si.addEventListener('click', () => _lazyToggle(sg, si, 'schema', { connId, schema: s }));
      sg.appendChild(si);
      sg.appendChild(_el('div', 'tree-group collapsed'));
      g.appendChild(sg);
    }
  }

  function setTables(connId, schema, tables) {
    const g = _schemaChildren(connId, schema); if (!g) return;
    g.innerHTML = '';
    for (const t of tables) {
      const tg = _el('div', 'tree-table', { 'data-table': t.name });
      const iconName = t.type === 'VIEW' ? 'view' : 'table';
      const ti = _treeItem(iconName, t.name, 2, true);
      ti.addEventListener('click', () => _lazyToggle(tg, ti, 'table', { connId, schema, table: t.name }));
      ti.addEventListener('dblclick', () => App.openTable(connId, schema, t.name));
      tg.appendChild(ti);
      tg.appendChild(_el('div', 'tree-group collapsed'));
      g.appendChild(tg);
    }
  }

  function setColumns(connId, schema, table, columns) {
    const g = _tableChildren(connId, schema, table); if (!g) return;
    g.innerHTML = '';
    for (const c of columns) {
      const ci = _treeItem('column', c.name, 3, false);
      const b  = _el('span', 'badge');
      b.textContent = c.data_type;
      if (c.primary_key) { b.innerHTML += ' ' + Icons.get('key', 10); }
      ci.appendChild(b);
      g.appendChild(ci);
    }
  }

  function removeConnection(connId) {
    dbTree().querySelector(`[data-conn="${connId}"]`)?.remove();
  }

  /* ══════════ SQL Scripts ══════════ */

  function refreshScripts(files) {
    const tree = scriptTree();
    tree.innerHTML = '';
    if (!files.length) {
      tree.innerHTML = '<div class="empty-hint" style="padding:12px">' + I18n.t('sidebar.noScripts') + '</div>';
      return;
    }
    for (const f of files) {
      const item = _treeItem('file-sql', f, 0, false);
      item.addEventListener('dblclick', () => App.openSqlFile(f));
      const del = _ctxBtn('disconnect', '删除', async e => {
        e.stopPropagation();
        if (confirm(`确认删除 ${f}？`)) await App.deleteSqlFile(f);
      });
      item.appendChild(del);
      tree.appendChild(item);
    }
  }

  /* ══════════ Helpers ══════════ */

  function _refreshActive() {
    if (AppState.activeConn) App.refreshConnection(AppState.activeConn);
  }

  function _onFilter(e) {
    const q = e.target.value.toLowerCase();
    dbTree().querySelectorAll('.tree-table').forEach(tg => {
      tg.style.display = !q || (tg.dataset.table || '').toLowerCase().includes(q) ? '' : 'none';
    });
  }

  function _el(tag, cls, attrs) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (attrs) Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    return e;
  }

  function _treeItem(iconName, label, depth, expandable) {
    const item = _el('div', 'tree-item');
    item.style.paddingLeft = `${12 + depth * 16}px`;
    if (expandable) {
      const a = _el('span', 'arrow'); a.textContent = '▸';
      item.appendChild(a);
    }
    if (iconName) { item.appendChild(Icons.el(iconName)); }
    const lbl = _el('span', 'label'); lbl.textContent = label;
    item.appendChild(lbl);
    return item;
  }

  function _ctxBtn(iconName, title, handler) {
    const b = _el('button', 'ctx-btn');
    b.innerHTML = Icons.get(iconName, 12); b.title = title;
    b.addEventListener('click', handler);
    return b;
  }

  function _toggle(group, item) {
    const children = group.querySelector(':scope > .tree-group');
    const arrow    = item.querySelector('.arrow');
    if (!children) return;
    const isOpen = !children.classList.contains('collapsed');
    children.classList.toggle('collapsed', isOpen);
    if (arrow) arrow.classList.toggle('open', !isOpen);
  }

  /** Lazy toggle: load children on first expand, then toggle */
  async function _lazyToggle(group, item, type, ctx) {
    const children = group.querySelector(':scope > .tree-group');
    const arrow    = item.querySelector('.arrow');
    if (!children) return;
    const isOpen = !children.classList.contains('collapsed');

    if (isOpen) {
      // Collapsing
      children.classList.add('collapsed');
      if (arrow) arrow.classList.remove('open');
      return;
    }

    // Expanding: lazy load if children empty, or always refresh for conn/schema
    const needLoad = children.children.length === 0;
    try {
      if (type === 'conn' && _onExpandConn) {
        // Always refresh schemas on expand
        await _onExpandConn(ctx.connId);
      } else if (type === 'schema' && _onExpandSchema) {
        await _onExpandSchema(ctx.connId, ctx.schema);
      } else if (type === 'table' && needLoad && _onExpandTable) {
        await _onExpandTable(ctx.connId, ctx.schema, ctx.table);
      }
    } catch (err) {
      console.error('Lazy load failed:', err);
    }

    children.classList.remove('collapsed');
    if (arrow) arrow.classList.add('open');
  }

  /** Register expand callbacks for lazy loading */
  function onExpand(handlers) {
    if (handlers.conn)   _onExpandConn   = handlers.conn;
    if (handlers.schema) _onExpandSchema  = handlers.schema;
    if (handlers.table)  _onExpandTable   = handlers.table;
  }

  /** Programmatically expand a path in the tree (conn → schema → table) */
  function expandPath(connId, schema, table) {
    const connEl = dbTree().querySelector(`[data-conn=\"${connId}\"]`);
    if (!connEl) return;
    // Expand connection
    const connGroup = connEl.querySelector(':scope > .tree-group');
    const connArrow = connEl.querySelector(':scope > .tree-item .arrow');
    if (connGroup) { connGroup.classList.remove('collapsed'); if (connArrow) connArrow.classList.add('open'); }
    // Expand schema
    if (schema) {
      const schemaEl = connEl.querySelector(`[data-schema=\"${schema}\"]`);
      if (schemaEl) {
        const schemaGroup = schemaEl.querySelector(':scope > .tree-group');
        const schemaArrow = schemaEl.querySelector(':scope > .tree-item .arrow');
        if (schemaGroup) { schemaGroup.classList.remove('collapsed'); if (schemaArrow) schemaArrow.classList.add('open'); }
        // Expand table
        if (table) {
          const tableEl = schemaEl.querySelector(`[data-table=\"${table}\"]`);
          if (tableEl) {
            const tableGroup = tableEl.querySelector(':scope > .tree-group');
            const tableArrow = tableEl.querySelector(':scope > .tree-item .arrow');
            if (tableGroup) { tableGroup.classList.remove('collapsed'); if (tableArrow) tableArrow.classList.add('open'); }
          }
        }
      }
    }
  }

  function _connChildren(id)              { const g = dbTree().querySelector(`[data-conn="${id}"]`); return g?.querySelector(':scope > .tree-group'); }
  function _schemaChildren(id, s)         { const g = dbTree().querySelector(`[data-conn="${id}"] [data-schema="${s}"]`); return g?.querySelector(':scope > .tree-group'); }
  function _tableChildren(id, s, t)       { const g = dbTree().querySelector(`[data-conn="${id}"] [data-schema="${s}"] [data-table="${t}"]`); return g?.querySelector(':scope > .tree-group'); }

  return { init, addConnection, setSchemas, setTables, setColumns, removeConnection, refreshScripts, onExpand, expandPath };
})();
