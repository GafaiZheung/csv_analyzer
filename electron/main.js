/**
 * Electron main process.
 *
 * - Workspace / filesystem management
 * - Python JSON-RPC backend (child process)
 * - Git operations
 * - IPC bridge to renderer
 */
const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path  = require('path');
const fs    = require('fs');
const { spawn, execFile } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
let CONFIG_PATH; // set after app ready

let mainWindow = null;
let pythonProc = null;
const pending  = new Map();

/* ══════════════════════ Config persistence ══════════════════════ */

function loadConfig() {
  try { return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8')); }
  catch { return {}; }
}

function saveConfig(cfg) {
  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
}

/* ══════════════════════ Python subprocess ══════════════════════ */

function startPython() {
  const venvPy = path.join(ROOT, '.venv', 'bin', 'python');
  const pyExe  = fs.existsSync(venvPy) ? venvPy : 'python3';
  const script = path.join(ROOT, 'csv_analyzer', 'backend', 'server.py');

  pythonProc = spawn(pyExe, [script], {
    cwd: ROOT,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  let buffer = '';
  pythonProc.stdout.on('data', chunk => {
    buffer += chunk.toString();
    let nl;
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      try {
        const resp = JSON.parse(line);
        const entry = pending.get(resp.msg_id);
        if (entry) {
          clearTimeout(entry.timer);
          pending.delete(resp.msg_id);
          entry.resolve(resp);
        }
      } catch (e) {
        console.error('[python stdout parse]', e.message);
      }
    }
  });

  pythonProc.stderr.on('data', d => {
    const msg = d.toString();
    console.error('[python]', msg);
    fs.appendFileSync('/tmp/dbanalyzer_python.log', msg);
  });
  pythonProc.on('exit', code => {
    console.log(`Python exited (${code})`);
    fs.appendFileSync('/tmp/dbanalyzer_python.log', `\n[EXIT] code=${code}\n`);
  });
}

function sendToPython(msg) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(msg.msg_id);
      reject(new Error('Python request timed out'));
    }, 60_000);
    pending.set(msg.msg_id, { resolve, timer });
    pythonProc.stdin.write(JSON.stringify(msg) + '\n');
  });
}

function stopPython() {
  if (!pythonProc) return;
  try { pythonProc.stdin.write(JSON.stringify({ action: 'shutdown' }) + '\n'); } catch {}
  setTimeout(() => { try { pythonProc.kill(); } catch {} }, 2000);
}

/* ══════════════════════ Window ══════════════════════ */

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    minWidth: 1000, minHeight: 660,
    backgroundColor: '#1e1e1e',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('closed', () => { mainWindow = null; });
}

/* ══════════════════════ IPC – Python RPC ══════════════════════ */

ipcMain.handle('rpc', async (_ev, req) => {
  try { return await sendToPython(req); }
  catch (e) { return { msg_id: req.msg_id, status: 'error', error: e.message, payload: {} }; }
});

/* ══════════════════════ IPC – Dialogs ══════════════════════ */

ipcMain.handle('open-file-dialog', async (_ev, opts) => {
  const defaults = {
    properties: ['openFile'],
    filters: [
      { name: 'CSV Files', extensions: ['csv', 'tsv', 'txt'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  };
  return dialog.showOpenDialog(mainWindow, { ...defaults, ...opts });
});

ipcMain.handle('select-folder', async () => {
  return dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    title: '选择工作区文件夹',
  });
});

/* ══════════════════════ IPC – App Config ══════════════════════ */

ipcMain.handle('get-config', () => loadConfig());
ipcMain.handle('save-config', (_ev, cfg) => { saveConfig(cfg); return true; });

/* ══════════════════════ IPC – File System ══════════════════════ */

ipcMain.handle('fs-read-dir', async (_ev, dirPath) => {
  try {
    const entries = await fs.promises.readdir(dirPath, { withFileTypes: true });
    return entries.map(e => ({ name: e.name, isDir: e.isDirectory() }));
  } catch { return []; }
});

ipcMain.handle('fs-read-file', async (_ev, filePath) => {
  return fs.promises.readFile(filePath, 'utf-8');
});

ipcMain.handle('fs-write-file', async (_ev, filePath, content) => {
  await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
  await fs.promises.writeFile(filePath, content, 'utf-8');
  return true;
});

ipcMain.handle('fs-delete-file', async (_ev, filePath) => {
  await fs.promises.unlink(filePath);
  return true;
});

ipcMain.handle('fs-ensure-dir', async (_ev, dirPath) => {
  await fs.promises.mkdir(dirPath, { recursive: true });
  return true;
});

ipcMain.handle('fs-exists', async (_ev, p) => {
  try { await fs.promises.access(p); return true; }
  catch { return false; }
});

/* ══════════════════════ IPC – Git ══════════════════════ */

ipcMain.handle('git-exec', (_ev, cwd, args) => {
  return new Promise(resolve => {
    execFile('git', args, { cwd, timeout: 30_000, maxBuffer: 1024 * 1024 }, (err, stdout, stderr) => {
      resolve({ ok: !err, code: err?.code ?? 0, stdout: stdout || '', stderr: stderr || '' });
    });
  });
});

/* ══════════════════════ IPC – Shell ══════════════════════ */

ipcMain.handle('open-external', (_ev, url) => shell.openExternal(url));

/* ══════════════════════ IPC – Pip install ══════════════════════ */

ipcMain.handle('pip-install', (_ev, packages) => {
  return new Promise(resolve => {
    const venvPip = path.join(ROOT, '.venv', 'bin', 'pip');
    const pipExe = fs.existsSync(venvPip) ? venvPip : 'pip3';
    const args = ['install', ...packages];
    execFile(pipExe, args, { cwd: ROOT, timeout: 120_000, maxBuffer: 2 * 1024 * 1024 }, (err, stdout, stderr) => {
      resolve({ ok: !err, stdout: stdout || '', stderr: stderr || '' });
    });
  });
});

ipcMain.handle('pip-check', (_ev, pkg) => {
  return new Promise(resolve => {
    const venvPython = path.join(ROOT, '.venv', 'bin', 'python');
    const pyExe = fs.existsSync(venvPython) ? venvPython : 'python3';
    execFile(pyExe, ['-c', `import ${pkg}`], { timeout: 10_000 }, (err) => {
      resolve(!err);
    });
  });
});

/* ══════════════════════ Lifecycle ══════════════════════ */

app.whenReady().then(() => {
  CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');
  startPython();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopPython();
  app.quit();
});
