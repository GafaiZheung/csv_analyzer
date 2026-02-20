/**
 * api.js – IPC wrapper for all backend/system calls.
 */
const API = (() => {
  let _seq = 0;
  const _id = () => `m_${Date.now()}_${++_seq}`;

  async function _rpc(action, target, payload = {}) {
    const msg = { action, target, msg_id: _id(), type: 'request', payload, status: 'pending' };
    const resp = await window.electronAPI.rpc(msg);
    if (resp.status === 'error') throw new Error(resp.error || 'Unknown error');
    return resp.payload;
  }

  return {
    /* ── Database ── */
    connect:      cfg                          => _rpc('connect',     'db', cfg),
    disconnect:   connId                       => _rpc('disconnect',  'db', { conn_id: connId }),
    getSchemas:   connId                       => _rpc('get_schemas', 'db', { conn_id: connId }),
    getTables:    (connId, schema)             => _rpc('get_tables',  'db', { conn_id: connId, schema }),
    getColumns:   (connId, schema, table)      => _rpc('get_columns', 'db', { conn_id: connId, schema, table }),
    executeSQL:   (connId, sql, limit=500, offset=0) =>
                    _rpc('execute_sql', 'db', { conn_id: connId, sql, limit, offset }),
    loadCSV:      (connId, csvPath)            => _rpc('load_csv',    'db', { conn_id: connId, csv_path: csvPath }),

    /* ── Analysis ── */
    columnStats:  (col, vals)   => _rpc('column_stats',   'analysis', { column: col, values: vals }),
    dataProfile:  (cols, rows)  => _rpc('data_profile',   'analysis', { columns: cols, rows }),
    missingValues:(cols, rows)  => _rpc('missing_values',  'analysis', { columns: cols, rows }),
    distribution: (col, vals)   => _rpc('distribution',   'analysis', { column: col, values: vals }),
    correlation:  (cols, rows)  => _rpc('correlation',     'analysis', { columns: cols, rows }),

    /* ── Workspace / FS ── */
    selectFolder:  ()           => window.electronAPI.selectFolder(),
    openFileDialog:(opts)       => window.electronAPI.openFileDialog(opts),
    getConfig:     ()           => window.electronAPI.getConfig(),
    saveConfig:    cfg          => window.electronAPI.saveConfig(cfg),
    readDir:       dir          => window.electronAPI.readDir(dir),
    readFile:      p            => window.electronAPI.readFile(p),
    writeFile:     (p, c)       => window.electronAPI.writeFile(p, c),
    deleteFile:    p            => window.electronAPI.deleteFile(p),
    ensureDir:     d            => window.electronAPI.ensureDir(d),
    fsExists:      p            => window.electronAPI.fsExists(p),

    /* ── Git ── */
    git:           (cwd, args)  => window.electronAPI.gitExec(cwd, args),

    /* ── Shell ── */
    openExternal:  url          => window.electronAPI.openExternal(url),

    /* ── Package Management ── */
    pipInstall:    pkgs         => window.electronAPI.pipInstall(pkgs),
    pipCheck:      pkg          => window.electronAPI.pipCheck(pkg),
  };
})();
