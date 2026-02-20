/**
 * state.js – application state with event emitter.
 */
const AppState = (() => {
  /* Workspace */
  let workspacePath = '';

  /* Connections: Map<connId, { name, dbType, config, schemas }> */
  const connections = new Map();
  let activeConn = '';

  /* Upper tabs (editors): Array<{ id, type, title, connId, pane, editor?, ... }> */
  const upperTabs = [];
  let activeUpperTabId = null;

  /* Lower tabs (results): Array<{ id, title, pane, ... }> */
  const lowerTabs = [];
  let activeLowerTabId = null;

  let _tabCounter = 0;

  /* Simple event bus */
  const _ls = {};
  function on(e, fn)  { (_ls[e] ||= []).push(fn); }
  function off(e, fn) { _ls[e] = (_ls[e] || []).filter(f => f !== fn); }
  function emit(e, d) { (_ls[e] || []).forEach(fn => fn(d)); }

  return {
    connections, upperTabs, lowerTabs,

    get workspacePath()    { return workspacePath; },
    set workspacePath(v)   { workspacePath = v; emit('workspace', v); },

    get activeConn()       { return activeConn; },
    set activeConn(v)      { activeConn = v; emit('active-conn', v); },

    get activeUpperTabId() { return activeUpperTabId; },
    set activeUpperTabId(v){ activeUpperTabId = v; emit('active-upper-tab', v); },

    get activeUpperTab()   { return upperTabs.find(t => t.id === activeUpperTabId) || null; },

    get activeLowerTabId() { return activeLowerTabId; },
    set activeLowerTabId(v){ activeLowerTabId = v; emit('active-lower-tab', v); },

    nextTabId() { return ++_tabCounter; },
    on, off, emit,
  };
})();
