import { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function Settings() {
  const [settings, setSettings] = useState<any>(null)
  const [codexStatus, setCodexStatus] = useState<any>(null)
  const [toolsStatus, setToolsStatus] = useState<any>(null)
  const [toast, setToast] = useState<string | null>(null)

  const [host, setHost] = useState('127.0.0.1')
  const [port, setPort] = useState(8899)
  const [logLevel, setLogLevel] = useState('info')
  const [autoStart, setAutoStart] = useState(false)
  const [closeToTray, setCloseToTray] = useState(true)

  useEffect(() => {
    api.getSettings().then((r) => {
      if (r?.server) {
        setSettings(r)
        setHost(r.server.host)
        setPort(r.server.port)
        setLogLevel(r.server.log_level)
        setAutoStart(r.server.auto_start)
        setCloseToTray(r.server.close_to_tray)
      }
    })
    api.getCodexStatus().then(setCodexStatus)
    api.getTools().then(setToolsStatus)
  }, [])

  const saveSettings = async () => {
    await api.updateSettings({ host, port, log_level: logLevel, auto_start: autoStart, close_to_tray: closeToTray })
    setToast('设置已保存')
    setTimeout(() => setToast(null), 2000)
  }

  const refreshCodex = async () => {
    const r = await api.getCodexStatus()
    setCodexStatus(r)
  }

  const applyCodex = async () => {
    const model = codexStatus?.current_model || 'deepseek-ai/DeepSeek-V3.2'
    const r = await api.applyCodexConfig(model, port)
    setToast(r?.status === 'ok' ? 'Codex 配置已写入' : '写入失败')
    refreshCodex()
    setTimeout(() => setToast(null), 2000)
  }

  const restoreCodex = async () => {
    const r = await api.restoreCodexConfig()
    setToast(r?.status === 'ok' ? 'Codex 配置已恢复' : '恢复失败')
    refreshCodex()
    setTimeout(() => setToast(null), 2000)
  }

  const toggleTool = async (name: string, enabled: boolean) => {
    await api.updateTools({ [name]: { enabled } })
    api.getTools().then(setToolsStatus)
  }

  return (
    <div>
      <h2 className="card-title" style={{ fontSize: 16, marginBottom: 20 }}>全局设置</h2>
      {toast && <div className={`toast ${toast.includes('失败') ? 'toast-error' : 'toast-success'}`}>{toast}</div>}

      <div className="card">
        <h3 className="card-title">服务器配置</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px', maxWidth: 500 }}>
          <div className="form-group">
            <label className="form-label">监听地址</label>
            <input className="form-input" value={host} onChange={(e) => setHost(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">端口</label>
            <input className="form-input" type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label className="form-label">日志级别</label>
            <select className="form-select" value={logLevel} onChange={(e) => setLogLevel(e.target.value)}>
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
        <div className="btn-group" style={{ marginTop: 12 }}>
          <button className="btn btn-primary" onClick={saveSettings}>保存设置</button>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Codex 配置管理</h3>
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 500, fontSize: 13 }}>配置目录:</span>
            <span style={{ fontSize: 13, color: codexStatus?.found ? 'var(--success)' : 'var(--danger)' }}>
              {codexStatus?.found ? codexStatus.dir : '未找到 .codex 目录'}
            </span>
            <button className="btn btn-outline btn-sm" onClick={refreshCodex}>刷新</button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
            备份状态: {codexStatus?.has_backup ? '✅ 备份存在' : '⚠️ 无备份'}
          </div>
          {codexStatus?.current_model && (
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>
              当前模型: {codexStatus.current_model} | 端口: {codexStatus.current_port}
            </div>
          )}
        </div>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={applyCodex}>
            写入配置 (使用代理)
          </button>
          <button className="btn btn-outline" onClick={restoreCodex} disabled={!codexStatus?.has_backup}>
            恢复默认配置
          </button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
          写入后 Codex 将使用本代理连接模型，恢复后还原原始配置
        </p>
      </div>

      <div className="card">
        <h3 className="card-title">服务端工具</h3>
        {toolsStatus?.tools && Object.entries(toolsStatus.tools).map(([name, info]: [string, any]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div>
              <div style={{ fontWeight: 500, fontSize: 13 }}>{name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {name === 'web_search' ? '自动执行 DuckDuckGo 搜索' : ''}
              </div>
            </div>
            <div className="toggle" onClick={() => toggleTool(name, !info.enabled)}>
              <div className={`toggle-switch ${info.enabled ? 'active' : ''}`} />
              <span style={{ fontSize: 12 }}>{info.enabled ? '启用' : '禁用'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
