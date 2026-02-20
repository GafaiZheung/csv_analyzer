/**
 * activity-bar.js – Left activity bar with view switching.
 */
const ActivityBar = (() => {
  const viewMap = {
    workspace:  'sidebar-workspace',
    git:        'sidebar-git',
    extensions: 'sidebar-extensions',
    settings:   'sidebar-settings',
  };

  function init() {
    document.querySelectorAll('.activity-btn[data-view]').forEach(btn => {
      btn.addEventListener('click', () => switchView(btn.dataset.view));
    });
  }

  function switchView(name) {
    document.querySelectorAll('.activity-btn[data-view]').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.activity-btn[data-view="${name}"]`);
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.sidebar-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(viewMap[name]);
    if (panel) panel.classList.add('active');

    // Trigger panel-specific refresh
    AppState.emit('view-changed', name);
  }

  return { init, switchView };
})();
