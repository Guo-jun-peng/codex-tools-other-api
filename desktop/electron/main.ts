import { app, BrowserWindow, Tray, Menu, ipcMain, shell } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import http from 'http'

const isDev = process.env.NODE_ENV !== 'production' || !app.isPackaged

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let pythonProcess: ChildProcess | null = null
const PROXY_PORT = 8899

function getApiBase(): string {
  return `http://127.0.0.1:${PROXY_PORT}/admin/api`
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    minWidth: 900,
    minHeight: 600,
    title: 'Codex 国内模型适配工具',
    icon: path.join(__dirname, '../public/icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    frame: true,
    titleBarStyle: 'default',
    backgroundColor: '#f5f7fa',
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function createTray() {
  // Tray icon - minimal
  tray = new Tray(path.join(__dirname, '../public/tray-icon.png'))
  const contextMenu = Menu.buildFromTemplate([
    { label: '显示主窗口', click: () => { mainWindow?.show(); mainWindow?.focus() } },
    { type: 'separator' },
    { label: '代理状态', enabled: false },
    { label: '退出', click: () => { stopProxy(); app.quit() } },
  ])
  tray.setToolTip('Codex 国内模型适配工具')
  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => { mainWindow?.show(); mainWindow?.focus() })
}

function startProxy() {
  if (pythonProcess) return

  const scriptPath = isDev
    ? path.join(__dirname, '../../codex_adapter_bridge/cli.py')
    : path.join(process.resourcesPath, 'backend', 'cli.py')

  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

  pythonProcess = spawn(pythonCmd, [
    '-m', 'codex_adapter_bridge.cli', 'start', '--port', String(PROXY_PORT)
  ], {
    cwd: isDev ? path.join(__dirname, '../..') : process.resourcesPath,
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  pythonProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[proxy] ${data.toString().trim()}`)
  })

  pythonProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[proxy:err] ${data.toString().trim()}`)
  })

  pythonProcess.on('close', (code: number | null) => {
    console.log(`[proxy] 进程退出, code=${code}`)
    pythonProcess = null
  })

  pythonProcess.on('error', (err: Error) => {
    console.error(`[proxy] 启动失败: ${err.message}`)
    pythonProcess = null
  })
}

function stopProxy() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

// IPC handlers
ipcMain.handle('get-proxy-status', async () => {
  return new Promise((resolve) => {
    http.get(`${getApiBase()}/status`, (res) => {
      let data = ''
      res.on('data', (chunk: string) => { data += chunk })
      res.on('end', () => {
        try { resolve(JSON.parse(data)) }
        catch { resolve({ running: false }) }
      })
    }).on('error', () => resolve({ running: false }))
  })
})

ipcMain.handle('api-fetch', async (_event, method: string, url: string, body?: unknown) => {
  return new Promise((resolve, reject) => {
    const fullUrl = `${getApiBase()}${url}`
    const data = body ? JSON.stringify(body) : undefined

    const req = http.request(fullUrl, {
      method,
      headers: { 'Content-Type': 'application/json' },
    }, (res) => {
      let responseData = ''
      res.on('data', (chunk: string) => { responseData += chunk })
      res.on('end', () => {
        try { resolve(JSON.parse(responseData)) }
        catch { resolve(responseData) }
      })
    })

    req.on('error', reject)
    if (data) req.write(data)
    req.end()
  })
})

app.whenReady().then(() => {
  createWindow()
  startProxy()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Keep proxy running in tray
  }
})

app.on('before-quit', () => {
  stopProxy()
})
