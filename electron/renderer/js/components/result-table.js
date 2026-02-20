/**
 * result-table.js – Renders query results into a <table>.
 * Works for both lower-panel result tabs and upper-panel table tabs.
 */
const ResultTable = (() => {
  const PAGE_SIZE = 500;

  function setResult(info, columns, rows, total, elapsed, offset) {
    const wrap    = info.pane.querySelector('.result-table-wrap');
    const footer  = info.pane.querySelector('.result-footer');
    const summary = footer.querySelector('.result-summary');
    const pageEl  = footer.querySelector('.page-info');

    info.offset = offset;
    info.total  = total;
    info._columns = columns;
    info._rows    = rows;

    // Build table
    const table = document.createElement('table');
    table.className = 'result-table';

    const thead = document.createElement('thead');
    const hr = document.createElement('tr');
    for (const col of columns) {
      const th = document.createElement('th');
      th.textContent = col; th.title = col;
      th.addEventListener('click', () => _onColumnClick(info, col, columns, rows));
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const val of row) {
        const td = document.createElement('td');
        if (val === null || val === undefined) {
          td.textContent = 'NULL'; td.className = 'null-cell';
        } else {
          td.textContent = String(val); td.title = String(val);
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);

    wrap.innerHTML = '';
    wrap.appendChild(table);

    // Footer
    summary.textContent = `${total.toLocaleString()} 行 · ${elapsed.toFixed(0)} ms`;
    const page  = Math.floor(offset / PAGE_SIZE) + 1;
    const pages = Math.ceil(total / PAGE_SIZE);
    pageEl.textContent = `${page} / ${pages}`;
    footer.classList.remove('hidden');
    footer.querySelector('[data-page="prev"]').disabled = offset <= 0;
    footer.querySelector('[data-page="next"]').disabled = offset + PAGE_SIZE >= total;
  }

  function setMessage(info, text, elapsed) {
    const wrap   = info.pane.querySelector('.result-table-wrap');
    const footer = info.pane.querySelector('.result-footer');
    wrap.innerHTML = `<div class="result-message">${_esc(text)}${elapsed ? ` · ${elapsed.toFixed(0)} ms` : ''}</div>`;
    footer.classList.add('hidden');
  }

  function setError(info, text) {
    const wrap   = info.pane.querySelector('.result-table-wrap');
    const footer = info.pane.querySelector('.result-footer');
    wrap.innerHTML = `<div class="result-message error">${_esc(text)}</div>`;
    footer.classList.add('hidden');
  }

  function _onColumnClick(info, colName, columns, rows) {
    const idx = columns.indexOf(colName);
    if (idx === -1) return;
    const values = rows.map(r => r[idx]);
    App.analyzeColumn(info, colName, values);
  }

  function _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  return { setResult, setMessage, setError, PAGE_SIZE };
})();
