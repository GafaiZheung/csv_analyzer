/**
 * icons.js – SVG icon library. All icons are inline SVG strings.
 * Usage: Icons.get('name') returns an SVG element string.
 */
const Icons = (() => {
  const _svgs = {
    /* ── Sidebar / Tree ── */
    database: `<svg viewBox="0 0 24 24" width="16" height="16"><ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" fill="none" stroke-width="1.4"/><path d="M4 6v4c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke="currentColor" fill="none" stroke-width="1.4"/><path d="M4 10v4c0 1.66 3.58 3 8 3s8-1.34 8-3v-4" stroke="currentColor" fill="none" stroke-width="1.4"/><path d="M4 14v4c0 1.66 3.58 3 8 3s8-1.34 8-3v-4" stroke="currentColor" fill="none" stroke-width="1.4"/></svg>`,

    folder: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/></svg>`,

    'folder-open': `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M5 19h14a2 2 0 001.84-1.22L23 12H7.16L5 17.78V19z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><path d="M3 7v10a2 2 0 002 2h14" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><path d="M3 7l2-2h4l2 2h10a2 2 0 012 2v1" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/></svg>`,

    table: `<svg viewBox="0 0 24 24" width="16" height="16"><rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" fill="none" stroke-width="1.4"/><line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="1.4"/><line x1="3" y1="15" x2="21" y2="15" stroke="currentColor" stroke-width="1.4"/><line x1="9" y1="3" x2="9" y2="21" stroke="currentColor" stroke-width="1.4"/></svg>`,

    view: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" fill="none" stroke-width="1.4"/><circle cx="12" cy="12" r="3" stroke="currentColor" fill="none" stroke-width="1.4"/></svg>`,

    key: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.78 7.78 5.5 5.5 0 017.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,

    file: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/></svg>`,

    'file-sql': `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><text x="8" y="17" font-size="7" fill="currentColor" font-family="sans-serif" font-weight="600">SQL</text></svg>`,

    'file-csv': `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><text x="7" y="17" font-size="7" fill="currentColor" font-family="sans-serif" font-weight="600">CSV</text></svg>`,

    close: `<svg viewBox="0 0 24 24" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,

    plus: `<svg viewBox="0 0 24 24" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,

    refresh: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M21 2v6h-6M3 12a9 9 0 0115-6.7L21 8M3 22v-6h6M21 12a9 9 0 01-15 6.7L3 16" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,

    /* ── Status Bar ── */
    'folder-sm': `<svg viewBox="0 0 24 24" width="14" height="14"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linejoin="round"/></svg>`,

    branch: `<svg viewBox="0 0 24 24" width="14" height="14"><line x1="6" y1="3" x2="6" y2="15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="18" cy="6" r="3" stroke="currentColor" fill="none" stroke-width="1.5"/><circle cx="6" cy="18" r="3" stroke="currentColor" fill="none" stroke-width="1.5"/><path d="M18 9a9 9 0 01-9 9" stroke="currentColor" fill="none" stroke-width="1.5"/></svg>`,

    /* ── Tab Icons ── */
    chart: `<svg viewBox="0 0 24 24" width="14" height="14"><line x1="18" y1="20" x2="18" y2="10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="20" x2="12" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="20" x2="6" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,

    play: `<svg viewBox="0 0 24 24" width="14" height="14"><polygon points="5 3 19 12 5 21 5 3" stroke="currentColor" fill="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,

    /* ── Extensions Panel ── */
    'chart-bar': `<svg viewBox="0 0 24 24" width="16" height="16"><line x1="18" y1="20" x2="18" y2="10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="20" x2="12" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="20" x2="6" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,

    server: `<svg viewBox="0 0 24 24" width="16" height="16"><rect x="2" y="2" width="20" height="8" rx="2" ry="2" stroke="currentColor" fill="none" stroke-width="1.4"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2" stroke="currentColor" fill="none" stroke-width="1.4"/><line x1="6" y1="6" x2="6.01" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="6" y1="18" x2="6.01" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,

    upload: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><polyline points="17 8 12 3 7 8" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,

    /* ── Misc ── */
    disconnect: `<svg viewBox="0 0 24 24" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,

    'new-file': `<svg viewBox="0 0 24 24" width="14" height="14"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><polyline points="14 2 14 8 20 8" stroke="currentColor" fill="none" stroke-width="1.4" stroke-linejoin="round"/><line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><line x1="9" y1="14" x2="15" y2="14" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`,

    settings: `<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="3" stroke="currentColor" fill="none" stroke-width="1.5"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" fill="none" stroke-width="1.5"/></svg>`,

    git: `<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="18" cy="18" r="3" stroke="currentColor" fill="none" stroke-width="1.5"/><circle cx="6" cy="6" r="3" stroke="currentColor" fill="none" stroke-width="1.5"/><path d="M13 6h3a2 2 0 012 2v7" stroke="currentColor" fill="none" stroke-width="1.5"/><line x1="6" y1="9" x2="6" y2="21" stroke="currentColor" stroke-width="1.5"/></svg>`,

    extensions: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linejoin="round"/></svg>`,

    workspace: `<svg viewBox="0 0 24 24" width="16" height="16"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linejoin="round"/></svg>`,

    column: `<svg viewBox="0 0 24 24" width="14" height="14"><rect x="4" y="4" width="16" height="16" rx="1" stroke="currentColor" fill="none" stroke-width="1.3"/><line x1="10" y1="4" x2="10" y2="20" stroke="currentColor" stroke-width="1.3"/></svg>`,
  };

  /**
   * Get an SVG icon HTML string by name.
   * @param {string} name  Icon name
   * @param {number} [size] Optional size override
   * @returns {string} SVG html string
   */
  function get(name, size) {
    let svg = _svgs[name];
    if (!svg) return '';
    if (size) {
      svg = svg.replace(/width="\d+"/, `width="${size}"`).replace(/height="\d+"/, `height="${size}"`);
    }
    return svg;
  }

  /**
   * Create an icon DOM element wrapped in a span.
   * @param {string} name
   * @param {string} [className]
   * @returns {HTMLElement}
   */
  function el(name, className) {
    const span = document.createElement('span');
    span.className = 'icon' + (className ? ' ' + className : '');
    span.innerHTML = get(name);
    return span;
  }

  return { get, el };
})();
