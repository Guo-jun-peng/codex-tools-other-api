import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface ModelForm { alias: string; target_model: string; provider: string; adapter: string; base_url: string; api_key: string; api_key_env: string; enabled: boolean }
const emptyForm: ModelForm = { alias: '', target_model: '', provider: '', adapter: '', base_url: '', api_key: '', api_key_env: '', enabled: true }

interface AdapterDefaults { base_url: string; api_key_env: string }

export default function Models() {
  const [models, setModels] = useState<any[]>([])
  const [adapters, setAdapters] = useState<string[]>([])
  const [adapterDefaults, setAdapterDefaults] = useState<Record<string, AdapterDefaults>>({})
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ModelForm>({ ...emptyForm })
  const [editingAlias, setEditingAlias] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<Record<string, any>>({})
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [loadError, setLoadError] = useState(false)

  const loadModels = async () => {
    setLoadError(false)
    const r = await api.getModels()
    if (r._error) { setLoadError(true); setModels([]); return }
    const ml = r?.models || []
    setModels(ml)
    if (ml.length === 0) setLoadError(true)
    if (ml.length > 0 && ml[0]?.available_adapters) {
      setAdapters(ml[0].available_adapters)
    }
  }

  useEffect(() => {
    loadModels()
    api.getAdapters().then(r => {
      if (!r._error && r.adapters) {
        const defaults: Record<string, AdapterDefaults> = {}
        r.adapters.forEach((a: any) => { defaults[a.name] = { base_url: a.base_url, api_key_env: a.api_key_env } })
        setAdapterDefaults(defaults)
      }
    })
  }, [])

  const showToast = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2500)
  }

  const resetForm = () => { setForm({ ...emptyForm }); setEditingAlias(null); setShowForm(false) }

  const editModel = (m: any) => {
    setForm({ alias: m.alias, target_model: m.target_model, provider: m.provider, adapter: m.adapter, base_url: m.base_url, api_key: '', api_key_env: m.api_key_env, enabled: m.enabled })
    setEditingAlias(m.alias); setShowForm(true)
  }

  const handleAdapterChange = (adapterName: string) => {
    if (!adapterName) {
      // "自动选择" — clear the fields
      setForm({ ...form, adapter: '', provider: '', base_url: '', api_key_env: '' })
      return
    }
    const defaults = adapterDefaults[adapterName]
    if (defaults) {
      setForm({ ...form, adapter: adapterName, provider: adapterName, base_url: defaults.base_url, api_key_env: defaults.api_key_env })
    } else {
      setForm({ ...form, adapter: adapterName, provider: adapterName })
    }
  }

  const saveModel = async () => {
    if (!form.alias || !form.target_model) { showToast('别名和目标模型为必填项', 'error'); return }
    setSaving(true)
    const data: any = { ...form }
    if (!data.api_key) delete data.api_key
    const r = editingAlias ? await api.updateModel(editingAlias, data) : await api.addModel(data)
    setSaving(false)
    if (r._error) { showToast(r._error, 'error'); return }
    showToast(editingAlias ? '模型已更新' : '模型已添加', 'success')
    resetForm(); loadModels()
  }

  const deleteModel = async (alias: string) => {
    if (!confirm(`确认删除模型 "${alias}"？`)) return
    const r = await api.deleteModel(alias)
    if (r._error) { showToast(r._error, 'error'); return }
    showToast('模型已删除', 'success')
    loadModels()
  }

  const toggleModel = async (alias: string) => {
    setToggling(alias)
    const r = await api.toggleModel(alias)
    setToggling(null)
    if (r._error) { showToast(r._error, 'error'); return }
    setModels(prev => prev.map(m => m.alias === alias ? { ...m, enabled: r.enabled } : m))
  }

  const testModel = async (alias: string) => {
    setTesting(alias)
    setTestResult(prev => ({ ...prev, [alias]: { status: 'testing', message: '测试中...' } }))
    const r = await api.testModel(alias)
    setTesting(null)
    if (r._error) { setTestResult(prev => ({ ...prev, [alias]: { status: 'error', message: r._error } })); return }
    setTestResult(prev => ({ ...prev, [alias]: r }))
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="card-title" style={{ fontSize: 16, margin: 0 }}>模型配置</h2>
        {!showForm && <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ 添加模型</button>}
      </div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}

      {showForm && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) resetForm() }}>
          <div className="modal">
            <h3 className="card-title">{editingAlias ? '编辑模型' : '添加模型'}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <div className="form-group"><label className="form-label">模型别名 (Codex 使用的名称)</label><input className="form-input" value={form.alias} placeholder="如: gpt-5-code" onChange={(e) => setForm({ ...form, alias: e.target.value })} disabled={!!editingAlias} /></div>
              <div className="form-group"><label className="form-label">目标模型</label><input className="form-input" value={form.target_model} placeholder="如: deepseek-ai/DeepSeek-V3.2" onChange={(e) => setForm({ ...form, target_model: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">提供商名称</label><input className="form-input" value={form.provider} placeholder="如: siliconflow" onChange={(e) => setForm({ ...form, provider: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">适配器</label><select className="form-select" value={form.adapter} onChange={(e) => handleAdapterChange(e.target.value)}><option value="">自动选择</option>{adapters.map((a) => <option key={a} value={a}>{a}</option>)}</select></div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}><label className="form-label">API 地址</label><input className="form-input" value={form.base_url} placeholder="如: https://api.siliconflow.cn/v1" onChange={(e) => setForm({ ...form, base_url: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">API Key</label><input className="form-input" type="password" value={form.api_key} placeholder={editingAlias ? '留空保持不变' : 'sk-...'} onChange={(e) => setForm({ ...form, api_key: e.target.value })} /></div>
              <div className="form-group"><label className="form-label">环境变量名</label><input className="form-input" value={form.api_key_env} placeholder="如: SILICONFLOW_API_KEY" onChange={(e) => setForm({ ...form, api_key_env: e.target.value })} /></div>
            </div>
            <div className="btn-group" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" onClick={saveModel} disabled={saving}>{saving ? '保存中...' : '保存'}</button>
              <button className="btn btn-outline" onClick={resetForm}>取消</button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table><thead><tr><th>别名</th><th>目标模型</th><th>适配器</th><th>API Key</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              {models.map((m: any) => {
                const tr = testResult[m.alias]
                return (
                  <tr key={m.alias}>
                    <td style={{ fontWeight: 500 }}>{m.alias}</td>
                    <td>{m.target_model}</td>
                    <td>{m.adapter || m.provider}</td>
                    <td><span className={`badge ${m.api_key_set ? 'badge-success' : 'badge-danger'}`}>{m.api_key_set ? '已设置' : '未设置'}</span></td>
                    <td>
                      <button
                        className={`toggle-switch ${m.enabled ? 'toggle-on' : 'toggle-off'}`}
                        onClick={() => toggleModel(m.alias)}
                        disabled={toggling === m.alias}
                        title={m.enabled ? '点击停用' : '点击启用'}
                      >
                        <span className="toggle-knob" />
                      </button>
                    </td>
                    <td>
                      <div className="btn-group">
                        <button className="btn btn-outline btn-sm" onClick={() => testModel(m.alias)} disabled={testing === m.alias}>{testing === m.alias ? '测试中...' : '测试'}</button>
                        <button className="btn btn-outline btn-sm" onClick={() => editModel(m)}>编辑</button>
                        <button className="btn btn-danger btn-sm" onClick={() => deleteModel(m.alias)}>删除</button>
                      </div>
                      {tr && <span className={`badge ${tr.status === 'ok' ? 'badge-success' : tr.status === 'testing' ? 'badge-warning' : 'badge-danger'}`} style={{ marginLeft: 8 }}>{tr.message?.slice(0, 30)}</span>}
                    </td>
                  </tr>
                )
              })}
              {loadError && models.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px 0' }}>
                  <div style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>加载失败或无已配置模型</div>
                  <button className="btn btn-primary btn-sm" onClick={loadModels}>重新加载</button>
                </td></tr>
              )}
              {!loadError && models.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>暂无模型，点击"添加模型"开始</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
