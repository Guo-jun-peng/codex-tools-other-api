import { useSettings } from '../hooks/useSettings'
import { useToast } from '../hooks/useToast'
import Toast from '../components/Toast'
import Modal from '../components/Modal'

export default function Settings() {
  const s = useSettings()
  const { toast, showToast, dismissToast } = useToast()

  const handleSave = async () => {
    const err = await s.saveSettings()
    if (err) { showToast(err, 'error'); return }
    showToast('设置已保存', 'success')
  }

  const handleApplyCodex = async () => {
    const err = await s.applyCodex()
    showToast(err ? err : 'Codex 配置已写入', err ? 'error' : 'success')
  }

  const handleRestoreCodex = async () => {
    const err = await s.restoreCodex()
    showToast(err ? err : 'Codex 配置已恢复', err ? 'error' : 'success')
  }

  return (
    <div>
      <h2 className="card-title" style={{ fontSize: 16, marginBottom: 20 }}>全局设置</h2>
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={dismissToast} />}

      <div className="card">
        <h3 className="card-title">服务器配置</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px', maxWidth: 500 }}>
          <div className="form-group"><label className="form-label">监听地址</label><input className="form-input" value={s.host} onChange={(e) => s.setHost(e.target.value)} /></div>
          <div className="form-group">
            <label className="form-label">端口 (1024-65535)</label>
            <input className="form-input" type="number" min={1024} max={65535} value={s.port} onChange={(e) => s.setPort(Number(e.target.value))} style={s.portError ? { borderColor: 'var(--danger)', boxShadow: '0 0 0 3px #fee2e2' } : {}} />
            {s.portError && <span className="form-hint" style={{ color: 'var(--danger)' }}>{s.portError}</span>}
          </div>
          <div className="form-group"><label className="form-label">日志级别</label><select className="form-select" value={s.logLevel} onChange={(e) => s.setLogLevel(e.target.value)}><option value="debug">Debug</option><option value="info">Info</option><option value="warning">Warning</option><option value="error">Error</option></select></div>
        </div>
        <div className="btn-group" style={{ marginTop: 12 }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={s.loading}>{s.loading ? '保存中...' : '保存设置'}</button>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Codex 配置管理</h3>
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 500, fontSize: 13 }}>配置目录:</span>
            <span style={{ fontSize: 13, color: s.codexStatus?.found ? 'var(--success)' : 'var(--danger)' }}>
              {s.codexStatus?.found ? s.codexStatus.dir : '未找到 .codex 目录'}
            </span>
            <button className="btn btn-outline btn-sm" onClick={s.refreshCodex}>刷新</button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>备份状态: {s.codexStatus?.has_backup ? '已备份' : '无备份'}</div>
          {s.codexStatus?.current_model && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 4 }}>当前模型: {s.codexStatus.current_model} | 端口: {s.codexStatus.current_port}</div>}
        </div>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={handleApplyCodex} disabled={s.codexLoading}>{s.codexLoading ? '处理中...' : '写入配置 (使用代理)'}</button>
          <button className="btn btn-outline" onClick={() => s.setShowRestoreConfirm(true)} disabled={!s.codexStatus?.has_backup || s.codexLoading}>恢复默认配置</button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>写入后 Codex 将使用本代理连接模型，恢复后还原原始配置</p>
      </div>

      {s.showRestoreConfirm && (
        <Modal title="确认恢复" variant="danger" onClose={() => s.setShowRestoreConfirm(false)}
          footer={<>
            <button className="btn btn-danger" onClick={handleRestoreCodex}>确认恢复</button>
            <button className="btn btn-outline" onClick={() => s.setShowRestoreConfirm(false)}>取消</button>
          </>}
        >
          <p style={{ marginBottom: 8 }}>确认恢复 Codex 到原始 OpenAI 配置？</p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20 }}>代理将停止工作，Codex 将使用默认 API。</p>
        </Modal>
      )}

      <div className="card">
        <h3 className="card-title">服务端工具</h3>
        {s.toolsStatus && Object.entries(s.toolsStatus).map(([name, info]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
            <div><div style={{ fontWeight: 500, fontSize: 13 }}>{name}</div><div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{name === 'web_search' ? '自动执行 DuckDuckGo 搜索' : ''}</div></div>
            <div className="toggle" onClick={() => s.toggleTool(name, !info.enabled)}><div className={`toggle-switch ${info.enabled ? 'active' : ''}`} /><span style={{ fontSize: 12 }}>{info.enabled ? '启用' : '禁用'}</span></div>
          </div>
        ))}
      </div>
    </div>
  )
}
