/**
 * analysis-panel.js – In-tab analysis panel (right side of data table tabs).
 * Sub-tabs: overview / stats / cell / calc
 */
const AnalysisPanel = (() => {

  function init() {}

  /**
   * Render overview (data_profile) into the table tab's analysis body.
   */
  function showOverview(info, data) {
    const body = _body(info); if (!body) return;
    body.innerHTML = '';

    const grid = _el('div', 'stat-grid');
    grid.appendChild(_card(I18n.t('analysis.totalRows'), data.row_count?.toLocaleString()));
    grid.appendChild(_card(I18n.t('analysis.totalCols'), data.col_count));
    body.appendChild(grid);

    if (data.columns) {
      _section(body, I18n.t('analysis.columnOverview'), () => {
        for (const col of data.columns) {
          const card = _el('div', 'stat-card');
          card.innerHTML = `
            <div class="stat-label">${_esc(col.name)} <span class="text-muted">${col.dtype}</span></div>
            <div class="stat-row"><span class="key">${I18n.t('analysis.nonNull')}</span><span class="val">${col.non_null}</span></div>
            <div class="stat-row"><span class="key">${I18n.t('analysis.nullPct')}</span><span class="val">${col.null_pct}%</span></div>
            <div class="stat-row"><span class="key">${I18n.t('analysis.unique')}</span><span class="val">${col.unique}</span></div>
          `;
          card.appendChild(_progressBar(100 - col.null_pct));
          body.appendChild(card);
        }
      });
    }
  }

  /**
   * Render column statistics into analysis body.
   */
  function showColumnStats(info, data) {
    const body = _body(info); if (!body) return;
    body.innerHTML = '';

    _section(body, `${I18n.t('analysis.column')}: ${data.column}`, () => {
      const grid = _el('div', 'stat-grid');
      grid.appendChild(_card(I18n.t('analysis.totalRows'), data.total));
      grid.appendChild(_card(I18n.t('analysis.nonNull'), data.non_null));
      grid.appendChild(_card(I18n.t('analysis.nullCount'), `${data.null_count} (${data.null_pct}%)`));
      grid.appendChild(_card(I18n.t('analysis.unique'), data.unique));
      body.appendChild(grid);

      if (data.dtype === 'numeric') {
        const g = _el('div', 'stat-grid');
        g.appendChild(_card(I18n.t('analysis.min'), _fmt(data.min)));
        g.appendChild(_card(I18n.t('analysis.max'), _fmt(data.max)));
        g.appendChild(_card(I18n.t('analysis.mean'), _fmt(data.mean)));
        g.appendChild(_card(I18n.t('analysis.std'), _fmt(data.std)));
        g.appendChild(_card(I18n.t('analysis.median'), _fmt(data.median)));
        g.appendChild(_card('P25', _fmt(data.p25)));
        g.appendChild(_card('P75', _fmt(data.p75)));
        body.appendChild(g);
      } else if (data.dtype === 'string') {
        const g = _el('div', 'stat-grid');
        g.appendChild(_card(I18n.t('analysis.shortest'), data.min_length));
        g.appendChild(_card(I18n.t('analysis.longest'), data.max_length));
        g.appendChild(_card(I18n.t('analysis.avgLength'), _fmt(data.avg_length)));
        body.appendChild(g);
      }

      if (data.null_pct > 0) body.appendChild(_progressBar(data.null_pct, data.null_pct > 50 ? 'error' : data.null_pct > 20 ? 'warning' : ''));
    });

    // Top values
    if (data.top_values?.length) {
      _section(body, I18n.t('analysis.topValues'), () => {
        const maxCnt = data.top_values[0].count;
        const ul = _el('ul', 'top-values');
        for (const tv of data.top_values) {
          const li = _el('li');
          const v = _el('span', 'tv-val'); v.textContent = tv.value;
          const bar = _el('span', 'tv-bar');
          const inner = _el('span'); inner.style.width = `${(tv.count / maxCnt * 100).toFixed(1)}%`;
          bar.appendChild(inner);
          const cnt = _el('span', 'tv-cnt'); cnt.textContent = tv.count;
          li.append(v, bar, cnt);
          ul.appendChild(li);
        }
        body.appendChild(ul);
      });
    }
  }

  /**
   * Show missing values analysis.
   */
  function showMissing(info, data) {
    const body = _body(info); if (!body) return;
    body.innerHTML = '';
    _section(body, `${I18n.t('analysis.missing')} (${data.total_rows} ${I18n.t('pagination.rows', data.total_rows)})`, () => {
      for (const col of data.columns) {
        const card = _el('div', 'stat-card');
        const cls = col.null_pct > 50 ? 'error' : col.null_pct > 20 ? 'warning' : '';
        card.innerHTML = `
          <div class="stat-label">${_esc(col.column)}</div>
          <div class="stat-row"><span class="key">${I18n.t('analysis.nullCount')}</span><span class="val ${cls ? 'text-' + cls : ''}">${col.null_count} (${col.null_pct}%)</span></div>
        `;
        card.appendChild(_progressBar(col.null_pct, cls));
        body.appendChild(card);
      }
    });
  }

  /**
   * Show distribution.
   */
  function showDistribution(info, data) {
    const body = _body(info); if (!body) return;
    _section(body, `${I18n.t('analysis.distribution')}: ${data.column}`, () => {
      const items = data.data || [];
      const maxCnt = Math.max(...items.map(d => d.count), 1);
      const ul = _el('ul', 'top-values');
      for (const item of items) {
        const li = _el('li');
        const v = _el('span', 'tv-val'); v.textContent = item.bin || item.value; v.style.minWidth = '100px';
        const bar = _el('span', 'tv-bar');
        const inner = _el('span'); inner.style.width = `${(item.count / maxCnt * 100).toFixed(1)}%`;
        bar.appendChild(inner);
        const cnt = _el('span', 'tv-cnt'); cnt.textContent = item.count;
        li.append(v, bar, cnt);
        ul.appendChild(li);
      }
      body.appendChild(ul);
    });
  }

  /**
   * Show correlation matrix.
   */
  function showCorrelation(info, data) {
    const body = _body(info); if (!body) return;
    body.innerHTML = '';

    if (!data.columns || data.columns.length < 2) {
      body.innerHTML = `<div class="empty-hint">${I18n.t('analysis.needTwoCols')}</div>`;
      return;
    }

    _section(body, I18n.t('analysis.correlation'), () => {
      const table = _el('table', 'result-table');
      table.style.fontSize = '11px';
      const thead = _el('thead');
      const hr = _el('tr');
      hr.appendChild(_el('th'));
      for (const c of data.columns) { const th = _el('th'); th.textContent = c; hr.appendChild(th); }
      thead.appendChild(hr);
      table.appendChild(thead);

      const tbody = _el('tbody');
      data.matrix.forEach((row, i) => {
        const tr = _el('tr');
        const th = _el('td'); th.textContent = data.columns[i]; th.style.fontWeight = '600'; tr.appendChild(th);
        for (const val of row) {
          const td = _el('td'); td.textContent = val.toFixed(2); td.style.textAlign = 'center';
          const abs = Math.abs(val);
          if (abs > 0.7) td.style.color = 'var(--success)';
          else if (abs > 0.4) td.style.color = 'var(--warning)';
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      body.appendChild(table);
    });
  }

  /**
   * Show cell value details.
   */
  function showCellInfo(info, colName, value) {
    const body = _body(info); if (!body) return;
    body.innerHTML = '';
    _section(body, I18n.t('analysis.cellValue'), () => {
      const card = _el('div', 'stat-card');
      card.innerHTML = `
        <div class="stat-label">${I18n.t('analysis.column')}: ${_esc(colName)}</div>
        <div class="stat-row"><span class="key">${I18n.t('analysis.value')}</span><span class="val">${_esc(String(value ?? 'NULL'))}</span></div>
        <div class="stat-row"><span class="key">${I18n.t('analysis.type')}</span><span class="val">${typeof value}</span></div>
        <div class="stat-row"><span class="key">${I18n.t('analysis.length')}</span><span class="val">${value != null ? String(value).length : 0}</span></div>
      `;
      body.appendChild(card);
    });
  }

  /* ── Helpers ── */
  function _body(info) { return info.pane.querySelector('.analysis-body'); }
  function _el(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function _fmt(v) { return v == null ? '—' : typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) : v; }
  function _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function _card(label, value) {
    const c = _el('div', 'stat-card');
    c.innerHTML = `<div class="stat-label">${label}</div><div class="stat-value">${_esc(String(value ?? '—'))}</div>`;
    return c;
  }

  function _progressBar(pct, variant) {
    const bar = _el('div', 'progress-bar');
    const fill = _el('div', 'fill' + (variant ? ` ${variant}` : ''));
    fill.style.width = `${Math.min(100, pct)}%`;
    bar.appendChild(fill);
    return bar;
  }

  function _section(parent, title, fn) {
    const sec = _el('div', 'analysis-section');
    const h4 = _el('h4'); h4.textContent = title;
    sec.appendChild(h4); parent.appendChild(sec); fn();
  }

  return { init, showOverview, showColumnStats, showMissing, showDistribution, showCorrelation, showCellInfo };
})();
