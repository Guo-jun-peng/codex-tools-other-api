import { useModels } from '../hooks/useModels'
import { useToast } from '../hooks/useToast'
import Toast from '../components/Toast'
import Modal from '../components/Modal'
import Badge from '../components/Badge'

export default function Models() {
  const m = useModels()
  const { toast, showToast, dismissToast } = useToast()

  const handleSave = async () => {
    const err = await m.saveModel()
    if (err) { showToast(err, 'error'); return }
    showToast(m.editingAlias ? '模型已更新' : '模型已添加', 'success')
  }

  const handleDelete = async () => {
    const err = await m.confirmDelete()
    if (err) showToast(err, 'error')
    else showToast('模型已删除', 'success')
  }

  const handleToggle = async (alias: string) => {
    const err = await m.toggleModel(alias)
    if (err) showToast(err, 'error')
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="card-title" style={{ fontSize: 16, margin: 0 }}>模型配置</h2>
        {!m.showForm && <button className="btn btn-primary" onClick={() => m.setShowForm(true)}>+ 添加模型</button>}
      </div>
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={dismissToast} />}

      {m.showForm && (
        <Modal
          title={m.editingAlias ? '编辑模型' : '添加模型'}
          onClose={m.resetForm}
          footer={<>
            <button className="btn btn-primary" onClick={handleSave} disabled={m.saving}>{m.saving ? '保存中...' : '保存'}</button>
            <button className="btn btn-outline" onClick={m.resetForm}>取消</button>
          </>}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <div className="form-group"><label className="form-label">模型别名 (Codex 使用的名称)</label><input className="form-input" value={m.form.alias} placeholder="如: gpt-5-code" onChange={(e) => m.setForm({ ...m.form, alias: e.target.value })} /></div>
            <div className="form-group"><label className="form-label">目标模型</label><input className="form-input" value={m.form.target_model} placeholder="如: deepseek-ai/DeepSeek-V3.2" onChange={(e) => m.setForm({ ...m.form, target_model: e.target.value })} /></div>
            <div className="form-group"><label className="form-label">提供商名称</label><input className="form-input" value={m.form.provider} placeholder="如: siliconflow" onChange={(e) => m.setForm({ ...m.form, provider: e.target.value })} /></div>
            <div className="form-group"><label className="form-label">适配器</label><select className="form-select" value={m.form.adapter} onChange={(e) => m.handleAdapterChange(e.target.value)}><option value="">自动选择</option>{m.adapters.map((a) => <option key={a} value={a}>{a}</option>)}</select></div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}><label className="form-label">API 地址</label><input className="form-input" value={m.form.base_url} placeholder="如: https://api.siliconflow.cn/v1" onChange={(e) => m.setForm({ ...m.form, base_url: e.target.value })} /></div>
            <div className="form-group"><label className="form-label">API Key</label><input className="form-input" type="password" value={m.form.api_key} placeholder={m.editingAlias ? '留空保持不变' : 'sk-...'} onChange={(e) => m.setForm({ ...m.form, api_key: e.target.value })} /><span className="form-hint">{m.editingAlias && m.isApiKeyMasked(m.form.api_key) ? '已设置 — 修改此值将更新 Key' : m.editingAlias ? '留空则保留原 Key' : ''}</span></div>
            <div className="form-group"><label className="form-label">环境变量名</label><input className="form-input" value={m.form.api_key_env} placeholder="如: SILICONFLOW_API_KEY" onChange={(e) => m.setForm({ ...m.form, api_key_env: e.target.value })} /></div>
          </div>
        </Modal>
      )}

      {m.deleteTarget && (
        <Modal title="确认删除" variant="danger" onClose={() => m.setDeleteTarget(null)}
          footer={<>
            <button className="btn btn-danger" onClick={handleDelete}>确认删除</button>
            <button className="btn btn-outline" onClick={() => m.setDeleteTarget(null)}>取消</button>
          </>}
        >
          <p style={{ marginBottom: 8 }}>确认删除模型 <strong>"{m.deleteTarget}"</strong>？</p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20 }}>删除后不可恢复，已配置的 Codex 将无法使用该模型。</p>
        </Modal>
      )}

      <div className="card">
        <div className="table-container">
          <table><thead><tr><th>别名</th><th>目标模型</th><th>适配器</th><th>API Key</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              {m.models.map((model) => {
                const tr = m.testResult[model.alias]
                return (
                  <tr key={model.alias}>
                    <td style={{ fontWeight: 500 }}>{model.alias}</td>
                    <td>{model.target_model}</td>
                    <td>{model.adapter || model.provider}</td>
                    <td><Badge variant={model.api_key_set ? 'success' : 'danger'}>{model.api_key_set ? (model.api_key_hint || '已设置') : '未设置'}</Badge></td>
                    <td>
                      <button
                        className={`toggle-switch ${model.enabled ? 'toggle-on' : 'toggle-off'}`}
                        onClick={() => handleToggle(model.alias)}
                        disabled={m.toggling === model.alias}
                        title={model.enabled ? '点击停用' : '点击启用'}
                      >
                        <span className="toggle-knob" />
                      </button>
                    </td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-outline btn-sm" onClick={() => m.testModel(model.alias)} disabled={m.testing === model.alias}>{m.testing === model.alias ? '测试中...' : '测试'}</button>
                        <button className="btn btn-outline btn-sm" onClick={() => m.editModel(model)}>编辑</button>
                        <button className="btn btn-danger btn-sm" onClick={() => m.setDeleteTarget(model.alias)}>删除</button>
                      </div>
                      {tr && <Badge variant={tr.status === 'ok' ? 'success' : tr.status === 'testing' ? 'warning' : 'danger'} style={{ marginLeft: 8 }}>{tr.message?.slice(0, 30)}</Badge>}
                    </td>
                  </tr>
                )
              })}
              {m.loadError && m.models.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px 0' }}>
                  <div style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>加载失败或无已配置模型</div>
                  <button className="btn btn-primary btn-sm" onClick={m.loadModels}>重新加载</button>
                </td></tr>
              )}
              {!m.loadError && m.models.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>暂无模型，点击"添加模型"开始</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
