/**
 * connection-dialog.js – Modal for creating database connections.
 */
const ConnectionDialog = (() => {
  const dlg  = () => document.getElementById('connection-dialog');
  const form = () => document.getElementById('connection-form');

  const GROUPS = {
    duckdb:     { host:false, port:false, database:false, user:false, password:false },
    sqlite:     { host:false, port:false, database:true,  user:false, password:false },
    postgresql: { host:true,  port:true,  database:true,  user:true,  password:true  },
    mysql:      { host:true,  port:true,  database:true,  user:true,  password:true  },
    /* Extra drivers – all use host/port/db/user/pwd */
    starrocks:  { host:true,  port:true,  database:true,  user:true,  password:true  },
    doris:      { host:true,  port:true,  database:true,  user:true,  password:true  },
    clickhouse: { host:true,  port:true,  database:true,  user:true,  password:true  },
    mssql:      { host:true,  port:true,  database:true,  user:true,  password:true  },
    oracle:     { host:true,  port:true,  database:true,  user:true,  password:true  },
    mariadb:    { host:true,  port:true,  database:true,  user:true,  password:true  },
  };
  const PORTS = { postgresql: 5432, mysql: 3306, starrocks: 9030, doris: 9030, clickhouse: 8123, mssql: 1433, oracle: 1521, mariadb: 3306 };

  function init() {
    document.getElementById('btn-cancel-conn').addEventListener('click', hide);
    form().addEventListener('submit', _onSubmit);
    document.getElementById('conn-db-type').addEventListener('change', _onTypeChange);
    dlg().addEventListener('click', e => { if (e.target === dlg()) hide(); });
    _onTypeChange();
  }

  function show() { form().reset(); _onTypeChange(); dlg().showModal(); }
  function hide() { dlg().close(); }

  function _onTypeChange() {
    const t = document.getElementById('conn-db-type').value;
    const vis = GROUPS[t] || GROUPS.duckdb;
    for (const [k, show] of Object.entries(vis)) {
      document.getElementById(`group-${k}`)?.classList.toggle('hidden', !show);
    }
    if (PORTS[t]) document.getElementById('conn-port').value = PORTS[t];
  }

  async function _onSubmit(e) {
    e.preventDefault();
    const dbType   = document.getElementById('conn-db-type').value;
    const host     = document.getElementById('conn-host').value;
    const port     = document.getElementById('conn-port').value;
    const database = document.getElementById('conn-database').value;
    const user     = document.getElementById('conn-user').value;
    const password = document.getElementById('conn-password').value;
    const name     = document.getElementById('conn-name').value;

    const connId = Math.random().toString(36).slice(2, 10);
    const config = { conn_id: connId, db_type: dbType, name: name || undefined };

    if (dbType === 'sqlite')        config.database = database;
    else if (dbType !== 'duckdb') { config.host = host; config.port = parseInt(port); config.database = database; config.user = user; config.password = password; }

    hide();
    App.createConnection(connId, config);
  }

  return { init, show, hide };
})();
