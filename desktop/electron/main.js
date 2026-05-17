const { app, BrowserWindow, Tray, Menu, nativeImage, dialog } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

// ── 单实例锁 ────────────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

const PROXY_PORT = 8899
const PROXY_URL = `http://127.0.0.1:${PROXY_PORT}`

let mainWindow = null
let tray = null
let pythonProcess = null

// ── 菜单栏中文化 ────────────────────────────────────────────
function buildChineseMenu() {
  const template = [
    {
      label: '文件(F)',
      submenu: [
        { label: '重新加载', accelerator: 'Ctrl+R', role: 'reload' },
        { type: 'separator' },
        { label: '退出', accelerator: 'Ctrl+Q', click: () => { stopPythonProxy(); app.exit(0) } },
      ],
    },
    {
      label: '编辑(E)',
      submenu: [
        { label: '撤销', accelerator: 'Ctrl+Z', role: 'undo' },
        { label: '重做', accelerator: 'Ctrl+Y', role: 'redo' },
        { type: 'separator' },
        { label: '剪切', accelerator: 'Ctrl+X', role: 'cut' },
        { label: '复制', accelerator: 'Ctrl+C', role: 'copy' },
        { label: '粘贴', accelerator: 'Ctrl+V', role: 'paste' },
        { label: '全选', accelerator: 'Ctrl+A', role: 'selectAll' },
      ],
    },
    {
      label: '查看(V)',
      submenu: [
        { label: '放大', accelerator: 'Ctrl+=', role: 'zoomIn' },
        { label: '缩小', accelerator: 'Ctrl+-', role: 'zoomOut' },
        { label: '重置缩放', accelerator: 'Ctrl+0', role: 'resetZoom' },
        { type: 'separator' },
        { label: '开发者工具', accelerator: 'F12', role: 'toggleDevTools' },
      ],
    },
    {
      label: '窗口(W)',
      submenu: [
        { label: '最小化', accelerator: 'Ctrl+M', role: 'minimize' },
        { label: '关闭', accelerator: 'Ctrl+W', click: () => mainWindow.hide() },
      ],
    },
    {
      label: '帮助(H)',
      submenu: [
        { label: '关于 Codex 适配器', click: () => {
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: '关于',
            message: 'Codex 国内模型适配工具',
            detail: '版本 1.0.0\n\n将 OpenAI Responses API 转换为 Chat Completions API，\n使 Codex CLI 无缝接入国产大模型。',
          })
        }},
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

// ── Python 代理 ──────────────────────────────────────────────
function startPythonProxy() {
  if (pythonProcess) return

  const pythonCmd = 'python'
  const isDev = !app.isPackaged
  const cwd = isDev
    ? path.join(__dirname, '../..')
    : path.join(process.resourcesPath, '..')

  pythonProcess = spawn(pythonCmd, [
    '-m', 'codex_adapter_bridge.cli', 'start',
    '--port', String(PROXY_PORT),
    '--no-open',
  ], {
    cwd: cwd,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
  })

  pythonProcess.on('close', (code) => { pythonProcess = null })
  pythonProcess.on('error', (err) => {
    dialog.showErrorBox('代理启动失败',
      `无法启动 Python 代理:\n${err.message}\n\n请检查 Python 是否已安装，依赖是否完整。`)
    pythonProcess = null
  })
}

function stopPythonProxy() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

// ── 等待代理就绪 ────────────────────────────────────────────
function waitForProxy(retries = 30) {
  return new Promise((resolve, reject) => {
    function check(n) {
      if (n <= 0) return reject(new Error('代理启动超时，请检查 Python 和依赖'))
      http.get(`${PROXY_URL}/health`, (res) => {
        if (res.statusCode === 200) resolve()
        else setTimeout(() => check(n - 1), 500)
      }).on('error', () => setTimeout(() => check(n - 1), 500))
    }
    check(retries)
  })
}

// ── 系统托盘 ────────────────────────────────────────────────
function createTray() {
  // Create a 16x16 colored icon programmatically (blue circle "C" dot)
  const size = 16
  const canvas = Buffer.alloc(size * size * 4)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4
      const cx = size / 2, cy = size / 2
      const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
      if (dist < size / 2 - 1) {
        canvas[idx] = 79; canvas[idx + 1] = 70; canvas[idx + 2] = 229; canvas[idx + 3] = 255 // #4F46E5
      } else {
        canvas[idx + 3] = 0
      }
    }
  }
  const icon = nativeImage.createFromBuffer(canvas, { width: size, height: size })
  tray = new Tray(icon)

  const menu = Menu.buildFromTemplate([
    { label: '显示主窗口', click: () => { mainWindow.show(); mainWindow.focus() } },
    { type: 'separator' },
    { label: '退出', click: () => { stopPythonProxy(); app.exit(0) } },
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

  mainWindow.webContents.session.clearCache()
  mainWindow.loadURL(PROXY_URL)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.on('close', (event) => {
    if (tray) {
      event.preventDefault()
      mainWindow.hide()
    }
  })

  mainWindow.on('closed', () => { mainWindow = null })
}

// ── 应用生命周期 ────────────────────────────────────────────
app.whenReady().then(async () => {
  buildChineseMenu()
  startPythonProxy()

  try {
    await waitForProxy(30)
  } catch (err) {
    dialog.showErrorBox('启动失败', err.message)
    app.quit()
    return
  }

  createTray()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else mainWindow.show()
  })
})

app.on('before-quit', () => {
  stopPythonProxy()
})
