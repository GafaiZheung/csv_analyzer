/**
 * Preload – exposes safe IPC bridge to renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /* Python RPC */
  rpc:            (req)          => ipcRenderer.invoke('rpc', req),

  /* Dialogs */
  openFileDialog: (opts)         => ipcRenderer.invoke('open-file-dialog', opts),
  selectFolder:   ()             => ipcRenderer.invoke('select-folder'),

  /* App config */
  getConfig:      ()             => ipcRenderer.invoke('get-config'),
  saveConfig:     (cfg)          => ipcRenderer.invoke('save-config', cfg),

  /* File system */
  readDir:        (dir)          => ipcRenderer.invoke('fs-read-dir', dir),
  readFile:       (p)            => ipcRenderer.invoke('fs-read-file', p),
  writeFile:      (p, c)         => ipcRenderer.invoke('fs-write-file', p, c),
  deleteFile:     (p)            => ipcRenderer.invoke('fs-delete-file', p),
  ensureDir:      (d)            => ipcRenderer.invoke('fs-ensure-dir', d),
  fsExists:       (p)            => ipcRenderer.invoke('fs-exists', p),

  /* Git */
  gitExec:        (cwd, args)    => ipcRenderer.invoke('git-exec', cwd, args),

  /* Shell */
  openExternal:   (url)          => ipcRenderer.invoke('open-external', url),

  /* Package management */
  pipInstall:     (pkgs)         => ipcRenderer.invoke('pip-install', pkgs),
  pipCheck:       (pkg)          => ipcRenderer.invoke('pip-check', pkg),
});
