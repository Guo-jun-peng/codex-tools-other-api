const { app, BrowserWindow, Tray, Menu, nativeImage } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

const isDev = !app.isPackaged
const PROXY_PORT = 8899
const PROXY_URL = `http://127.0.0.1:${PROXY_PORT}`

let mainWindow = null
let tray = null
let pythonProcess = null

// ── Python 代理 ──────────────────────────────────────────────
function startPythonProxy() {
  if (pythonProcess) return

  const pythonCmd = 'python'
  const cwd = isDev
    ? path.join(__dirname, '../..')
    : path.join(process.resourcesPath, '..')

  console.log(`[main] Starting Python proxy in ${cwd}`)

  pythonProcess = spawn(pythonCmd, [
    '-m', 'codex_adapter_bridge.cli', 'start',
    '--port', String(PROXY_PORT),
    '--no-open'
  ], {
    cwd: cwd,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[proxy] ${data.toString().trim()}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[proxy:err] ${data.toString().trim()}`)
  })

  pythonProcess.on('close', (code) => {
    console.log(`[proxy] exited with code ${code}`)
    pythonProcess = null
  })

  pythonProcess.on('error', (err) => {
    console.error(`[proxy] spawn failed: ${err.message}`)
    pythonProcess = null
  })
}

function stopPythonProxy() {
  if (pythonProcess) {
    console.log('[main] Stopping Python proxy')
    pythonProcess.kill()
    pythonProcess = null
  }
}

// ── 等待代理就绪 ────────────────────────────────────────────
function waitForProxy(retries = 20) {
  return new Promise((resolve, reject) => {
    function check(n) {
      if (n <= 0) {
        return reject(new Error('Proxy startup timeout'))
      }
      http.get(`${PROXY_URL}/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[main] Proxy is ready')
          resolve()
        } else {
          setTimeout(() => check(n - 1), 500)
        }
      }).on('error', () => {
        setTimeout(() => check(n - 1), 500)
      })
    }
    check(retries)
  })
}

// ── 系统托盘 ────────────────────────────────────────────────
function createTray() {
  // Create a simple 16x16 icon
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)

  const menu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => { mainWindow.show(); mainWindow.focus() }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        stopPythonProxy()
        app.quit()
      }
    },
  ])

  tray.setToolTip('Codex 国内模型适配工具')
  tray.setContextMenu(menu)
  tray.on('double-click', () => { mainWindow.show(); mainWindow.focus() })
}

// ── 主窗口 ──────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 900,
    minHeight: 600,
    title: 'Codex 国内模型适配工具',
    backgroundColor: '#f0f2f5',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Clear cache to ensure fresh frontend load
  mainWindow.webContents.session.clearCache()

  mainWindow.loadURL(PROXY_URL)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  // Normal close - quit app (stop proxy + exit)
  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── 应用生命周期 ────────────────────────────────────────────
app.whenReady().then(async () => {
  startPythonProxy()

  try {
    await waitForProxy(30)
  } catch (err) {
    console.error('[main] Failed to start proxy:', err.message)
    app.quit()
    return
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else mainWindow.show()
  })
})

app.on('window-all-closed', () => {
  // Don't quit on macOS
})

app.on('before-quit', () => {
  stopPythonProxy()
})
