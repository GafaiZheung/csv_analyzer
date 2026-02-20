/**
 * git-panel.js – Git version management sidebar panel with commit graph.
 */
const GitPanel = (() => {
  const el = () => document.getElementById('git-content');
  let _initialized = false;

  /* Branch colors for the graph */
  const GRAPH_COLORS = [
    '#4fc1ff', '#89d185', '#cca700', '#f44747',
    '#c586c0', '#ce9178', '#569cd6', '#d7ba7d',
  ];

  function init() {
    AppState.on('view-changed', view => {
      if (view === 'git') refresh();
    });
  }

  async function refresh() {
    const ws = AppState.workspacePath;
    if (!ws) { _showMsg(I18n.t('git.selectWorkspace')); return; }

    const container = el();
    container.innerHTML = '<div class="empty-hint"><div class="spinner"></div></div>';

    const isGit = await API.fsExists(ws + '/.git');

    if (!isGit) {
      container.innerHTML = `
        <div class="empty-hint">
          <p>${I18n.t('git.notInitialized')}</p>
          <button class="btn btn-primary btn-sm" id="btn-git-init">${I18n.t('git.initRepo')}</button>
        </div>
      `;
      document.getElementById('btn-git-init').addEventListener('click', _initRepo);
      return;
    }

    // Get status, branch, remote, AND commit log in parallel
    const [statusRes, branchRes, remoteRes, logRes] = await Promise.all([
      API.git(ws, ['status', '--porcelain']),
      API.git(ws, ['branch', '--show-current']),
      API.git(ws, ['remote', '-v']),
      API.git(ws, [
        'log', '--all', '--pretty=format:%H|%h|%P|%D|%s|%an|%ar', '--max-count=80',
      ]),
    ]);

    const branch = branchRes.ok ? branchRes.stdout.trim() : 'unknown';
    StatusBar.setBranch(branch);

    const files = statusRes.ok ? statusRes.stdout.trim().split('\n').filter(Boolean).map(l => ({
      status: l.substring(0, 2).trim(),
      file: l.substring(3),
    })) : [];

    const remoteLines = remoteRes.ok ? remoteRes.stdout.trim() : '';
    const remoteUrl = remoteLines ? (remoteLines.split('\n')[0]?.split(/\s+/)[1] || '') : '';

    const commits = _parseLog(logRes);

    _render(files, branch, remoteUrl, commits);
  }

  /* ── Parse git log into structured commits ── */
  function _parseLog(logRes) {
    if (!logRes.ok || !logRes.stdout.trim()) return [];
    return logRes.stdout.trim().split('\n').filter(Boolean).map(line => {
      const [hash, short, parents, refs, message, author, date] = line.split('|');
      return {
        hash, short, message, author, date,
        parents: parents ? parents.split(' ').filter(Boolean) : [],
        refs: refs ? refs.split(',').map(r => r.trim()).filter(Boolean) : [],
      };
    });
  }

  /* ── Build commit graph layout ── */
  function _buildGraph(commits) {
    // Each commit gets a column assignment. Active lanes track ongoing branches.
    const lanes = []; // active commit hashes occupying each lane
    const layout = []; // { commit, col, edges: [{fromCol, toCol, color}], laneCount }
    const colorMap = new Map();
    let colorIdx = 0;

    function getColor(hash) {
      if (!colorMap.has(hash)) colorMap.set(hash, GRAPH_COLORS[colorIdx++ % GRAPH_COLORS.length]);
      return colorMap.get(hash);
    }

    for (const commit of commits) {
      let col = lanes.indexOf(commit.hash);
      if (col === -1) {
        // New branch – find an empty lane or append
        col = lanes.indexOf(null);
        if (col === -1) { col = lanes.length; lanes.push(null); }
        lanes[col] = commit.hash;
      }

      const color = getColor(commit.hash);
      const edges = [];

      // Connect parents
      const parents = commit.parents;
      for (let pi = 0; pi < parents.length; pi++) {
        const parentHash = parents[pi];
        let parentCol = lanes.indexOf(parentHash);
        if (pi === 0) {
          // First parent takes current lane
          lanes[col] = parentHash;
          parentCol = col;
          colorMap.set(parentHash, color); // inherit color
        } else {
          // Merge parent – find or create lane
          if (parentCol === -1) {
            parentCol = lanes.indexOf(null);
            if (parentCol === -1) { parentCol = lanes.length; lanes.push(null); }
            lanes[parentCol] = parentHash;
          }
        }
        edges.push({ fromCol: col, toCol: parentCol, color: getColor(parentHash) });
      }

      if (parents.length === 0) {
        // Root commit – close lane
        lanes[col] = null;
      }

      // Continuation lines for other active lanes
      for (let i = 0; i < lanes.length; i++) {
        if (i !== col && lanes[i] != null) {
          edges.push({ fromCol: i, toCol: i, color: getColor(lanes[i]) });
        }
      }

      layout.push({ commit, col, edges, color, laneCount: lanes.length });

      // Clean up trailing null lanes
      while (lanes.length > 0 && lanes[lanes.length - 1] === null) lanes.pop();
    }
    return layout;
  }

  /* ── Render SVG graph + commit list ── */
  function _renderGraph(commits) {
    if (commits.length === 0) {
      return `<div style="font-size:12px;color:var(--fg-dim);padding:4px 0">${I18n.t('git.noCommits')}</div>`;
    }

    const layout = _buildGraph(commits);
    const ROW_H = 28;
    const COL_W = 14;
    const R = 4;
    const PAD_LEFT = 4;

    const maxLanes = Math.max(...layout.map(l => l.laneCount), 1);
    const graphW = PAD_LEFT + maxLanes * COL_W + 8;
    const totalH = layout.length * ROW_H;

    let svg = `<svg width="${graphW}" height="${totalH}" class="git-graph-svg">`;

    // Draw edges first (behind nodes)
    for (let i = 0; i < layout.length; i++) {
      const y = i * ROW_H + ROW_H / 2;
      const yNext = y + ROW_H;
      for (const edge of layout[i].edges) {
        const x1 = PAD_LEFT + edge.fromCol * COL_W + COL_W / 2;
        const x2 = PAD_LEFT + edge.toCol * COL_W + COL_W / 2;
        if (i < layout.length - 1) {
          if (x1 === x2) {
            svg += `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${yNext}" stroke="${edge.color}" stroke-width="1.5" opacity="0.7"/>`;
          } else {
            svg += `<path d="M${x1},${y} C${x1},${y + ROW_H * 0.4} ${x2},${yNext - ROW_H * 0.4} ${x2},${yNext}" stroke="${edge.color}" stroke-width="1.5" fill="none" opacity="0.7"/>`;
          }
        }
      }
    }

    // Draw nodes
    for (let i = 0; i < layout.length; i++) {
      const y = i * ROW_H + ROW_H / 2;
      const x = PAD_LEFT + layout[i].col * COL_W + COL_W / 2;
      const isMerge = layout[i].commit.parents.length > 1;
      svg += `<circle cx="${x}" cy="${y}" r="${isMerge ? R + 1 : R}" fill="${layout[i].color}" stroke="var(--bg-sidebar)" stroke-width="1.5"/>`;
    }

    svg += '</svg>';

    // Build rows
    let rows = '';
    for (let i = 0; i < layout.length; i++) {
      const c = layout[i].commit;
      const refsHtml = c.refs.map(r => {
        const isHead = r.startsWith('HEAD');
        const isBranch = !r.startsWith('tag:');
        const cls = isHead ? 'git-ref head' : (isBranch ? 'git-ref branch' : 'git-ref tag');
        return `<span class="${cls}">${_esc(r)}</span>`;
      }).join('');
      rows += `<div class="git-graph-row" style="height:${ROW_H}px" title="${_esc(c.hash)}">
        <span class="git-graph-info">
          ${refsHtml}
          <span class="git-graph-msg">${_esc(c.message)}</span>
        </span>
        <span class="git-graph-meta">
          <span class="git-graph-hash">${_esc(c.short)}</span>
          <span class="git-graph-date">${_esc(c.date)}</span>
        </span>
      </div>`;
    }

    return `<div class="git-graph-container">
      <div class="git-graph-canvas">${svg}</div>
      <div class="git-graph-rows">${rows}</div>
    </div>`;
  }

  function _render(files, branch, remoteUrl, commits) {
    const container = el();
    container.innerHTML = '';

    // Branch info
    const branchDiv = _el('div', 'git-section');
    branchDiv.innerHTML = `<div class="git-section-title">${I18n.t('git.branch')}: ${_esc(branch)}</div>`;
    container.appendChild(branchDiv);

    // Changed files
    const changesDiv = _el('div', 'git-section');
    changesDiv.innerHTML = `<div class="git-section-title">${I18n.t('git.changes')} (${files.length})</div>`;
    if (files.length === 0) {
      changesDiv.innerHTML += `<div style="font-size:12px;color:var(--fg-dim);padding:4px 0">${I18n.t('git.noChanges')}</div>`;
    } else {
      for (const f of files) {
        const cls = f.status === 'M' ? 'modified' : f.status === 'A' ? 'added' : f.status === 'D' ? 'deleted' : 'untracked';
        const badge = f.status === '?' ? 'U' : f.status;
        const item = _el('div', 'git-file');
        item.innerHTML = `<span class="git-status-badge ${cls}">${badge}</span><span class="label">${_esc(f.file)}</span>`;
        changesDiv.appendChild(item);
      }
    }
    container.appendChild(changesDiv);

    // Commit section
    const commitDiv = _el('div', 'git-section');
    commitDiv.innerHTML = `
      <div class="git-section-title">${I18n.t('git.commit')}</div>
      <textarea class="git-input textarea" id="git-commit-msg" placeholder="${I18n.t('git.commitMsg')}" rows="3"></textarea>
      <div class="git-btn-row">
        <button class="btn btn-sm btn-secondary" id="btn-git-add-all">${I18n.t('git.stageAll')}</button>
        <button class="btn btn-sm btn-primary" id="btn-git-commit">${I18n.t('git.commit')}</button>
      </div>
    `;
    container.appendChild(commitDiv);

    // Remote section
    const remoteDiv = _el('div', 'git-section');
    remoteDiv.innerHTML = `
      <div class="git-section-title">${I18n.t('git.remote')}</div>
      <input class="git-input" id="git-remote-url" placeholder="${I18n.t('git.remoteUrl')}" value="${_esc(remoteUrl)}">
      <div class="git-btn-row">
        <button class="btn btn-sm btn-secondary" id="btn-git-set-remote">${remoteUrl ? I18n.t('git.updateRemote') : I18n.t('git.addRemote')}</button>
        <button class="btn btn-sm btn-primary" id="btn-git-push">${I18n.t('git.push')}</button>
      </div>
    `;
    container.appendChild(remoteDiv);

    // ── Version Tree (commit graph) ──
    const graphDiv = _el('div', 'git-section');
    graphDiv.innerHTML = `<div class="git-section-title">${I18n.t('git.history')}</div>`;
    const graphContent = _el('div', '');
    graphContent.innerHTML = _renderGraph(commits);
    graphDiv.appendChild(graphContent);
    container.appendChild(graphDiv);

    // Wire events
    document.getElementById('btn-git-add-all').addEventListener('click', _addAll);
    document.getElementById('btn-git-commit').addEventListener('click', _commit);
    document.getElementById('btn-git-set-remote').addEventListener('click', _setRemote);
    document.getElementById('btn-git-push').addEventListener('click', _push);
  }

  async function _initRepo() {
    const ws = AppState.workspacePath;
    const res = await API.git(ws, ['init']);
    if (res.ok) {
      const ignoreExists = await API.fsExists(ws + '/.gitignore');
      if (!ignoreExists) {
        await API.writeFile(ws + '/.gitignore', '__pycache__/\n*.pyc\nnode_modules/\n.venv/\n*.egg-info/\n.dbanalyzer/settings.json\n');
      }
      refresh();
    } else {
      alert(I18n.t('git.initFailed') + ': ' + res.stderr);
    }
  }

  async function _addAll() {
    const res = await API.git(AppState.workspacePath, ['add', '-A']);
    if (res.ok) refresh();
    else alert(I18n.t('git.stageFailed') + ': ' + res.stderr);
  }

  async function _commit() {
    const msg = document.getElementById('git-commit-msg')?.value?.trim();
    if (!msg) { alert(I18n.t('git.enterCommitMsg')); return; }
    const addRes = await API.git(AppState.workspacePath, ['add', '-A']);
    if (!addRes.ok) { alert(I18n.t('git.stageFailed') + ': ' + addRes.stderr); return; }
    const res = await API.git(AppState.workspacePath, ['commit', '-m', msg]);
    if (res.ok) { StatusBar.setInfo(I18n.t('git.committed')); refresh(); }
    else alert(I18n.t('git.commitFailed') + ': ' + (res.stderr || res.stdout));
  }

  async function _setRemote() {
    const url = document.getElementById('git-remote-url')?.value?.trim();
    if (!url) return;
    const ws = AppState.workspacePath;
    let res = await API.git(ws, ['remote', 'set-url', 'origin', url]);
    if (!res.ok) res = await API.git(ws, ['remote', 'add', 'origin', url]);
    if (res.ok) { StatusBar.setInfo(I18n.t('git.remoteSet')); refresh(); }
    else alert(I18n.t('git.setRemoteFailed') + ': ' + res.stderr);
  }

  async function _push() {
    StatusBar.setInfo(I18n.t('git.pushing'));
    const ws = AppState.workspacePath;
    const br = await API.git(ws, ['branch', '--show-current']);
    const branch = br.ok ? br.stdout.trim() : 'main';
    const res = await API.git(ws, ['push', '-u', 'origin', branch]);
    if (res.ok) StatusBar.setInfo(I18n.t('git.pushSuccess'));
    else {
      StatusBar.setInfo(I18n.t('git.pushFailed'));
      alert(I18n.t('git.pushFailed') + ': ' + (res.stderr || res.stdout));
    }
  }

  function _showMsg(msg) { el().innerHTML = `<div class="empty-hint">${msg}</div>`; }
  function _el(tag, cls) { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function _esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  return { init, refresh };
})();
