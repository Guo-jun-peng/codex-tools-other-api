import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface ModelForm {
  alias: string
  target_model: string
  provider: string
  adapter: string
  base_url: string
  api_key: string
  api_key_env: string
  enabled: boolean
}

const emptyForm: ModelForm = {
  alias: '', target_model: '', provider: '', adapter: '',
  base_url: '', api_key: '', api_key_env: '', enabled: true,
}

export default function Models() {
  const [models, setModels] = useState<any[]>([])
  const [adapters, setAdapters] = useState<string[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ModelForm>({ ...emptyForm })
  const [editingAlias, setEditingAlias] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any>(null)
  const [toast, setToast] = useState<string | null>(null)

  const loadModels = async () => {
    const r = await api.getModels()
    setModels(r?.models || [])
  }

  useEffect(() => { loadModels() }, [])

  useEffect(() => {
    api.getModels().then((r) => {
      if (r?.models?.length > 0) {
        setAdapters(r.models[0]?.available_adapters || [])
      }
    })
  }, [models])

  const resetForm = () => {
    setForm({ ...emptyForm })
    setEditingAlias(null)
    setShowForm(false)
  }

  const editModel = (m: any) => {
    setForm({
      alias: m.alias,
      target_model: m.target_model,
      provider: m.provider,
      adapter: m.adapter,
      base_url: m.base_url,
      api_key: '',
      api_key_env: m.api_key_env,
      enabled: m.enabled,
    })
    setEditingAlias(m.alias)
    setShowForm(true)
  }

  const saveModel = async () => {
    if (!form.alias || !form.target_model) {
      setToast('别名和目标模型为必填项')
      return
    }
    const data: any = { ...form }
    if (!data.api_key) delete data.api_key

    if (editingAlias) {
      await api.updateModel(editingAlias, data)
      setToast('模型已更新')
    } else {
      await api.addModel(data)
      setToast('模型已添加')
    }
    resetForm()
    loadModels()
    setTimeout(() => setToast(null), 2000)
  }

  const deleteModel = async (alias: string) => {
    if (!confirm(`确认删除模型 "${alias}"？`)) return
    await api.deleteModel(alias)
    setToast('模型已删除')
    loadModels()
    setTimeout(() => setToast(null), 2000)
  }

  const testModel = async (alias: string) => {
    setTestResult({ alias, status: 'testing', message: '测试中...' })
    const r = await api.testModel(alias)
    setTestResult({ alias, ...r })
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="card-title" style={{ fontSize: 16, margin: 0 }}>模型配置</h2>
        <div className="btn-group">
          {!showForm && (
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ 添加模型</button>
          )}
        </div>
      </div>

      {toast && <div className="toast toast-success">{toast}</div>}

      {showForm && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) resetForm() }}>
          <div className="modal">
            <h3 className="card-title">{editingAlias ? '编辑模型' : '添加模型'}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
              <div className="form-group">
                <label className="form-label">模型别名 (Codex 使用的名称)</label>
                <input className="form-input" value={form.alias} placeholder="如: gpt-5-code"
                  onChange={(e) => setForm({ ...form, alias: e.target.value })} disabled={!!editingAlias} />
              </div>
              <div className="form-group">
                <label className="form-label">目标模型</label>
                <input className="form-input" value={form.target_model} placeholder="如: deepseek-ai/DeepSeek-V3.2"
                  onChange={(e) => setForm({ ...form, target_model: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">提供商名称</label>
                <input className="form-input" value={form.provider} placeholder="如: siliconflow"
                  onChange={(e) => setForm({ ...form, provider: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">适配器</label>
                <select className="form-select" value={form.adapter}
                  onChange={(e) => setForm({ ...form, adapter: e.target.value })}>
                  <option value="">自动选择</option>
                  {adapters.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">API 地址</label>
                <input className="form-input" value={form.base_url} placeholder="如: https://api.siliconflow.cn/v1"
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">API Key</label>
                <input className="form-input" type="password" value={form.api_key} placeholder="sk-..."
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">环境变量名</label>
                <input className="form-input" value={form.api_key_env} placeholder="如: SILICONFLOW_API_KEY"
                  onChange={(e) => setForm({ ...form, api_key_env: e.target.value })} />
              </div>
            </div>
            <div className="btn-group" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" onClick={saveModel}>保存</button>
              <button className="btn btn-outline" onClick={resetForm}>取消</button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>别名</th>
                <th>目标模型</th>
                <th>适配器</th>
                <th>API Key</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m: any) => (
                <tr key={m.alias}>
                  <td style={{ fontWeight: 500 }}>{m.alias}</td>
                  <td>{m.target_model}</td>
                  <td>{m.adapter || m.provider}</td>
                  <td>
                    <span className={`badge ${m.api_key_set ? 'badge-success' : 'badge-danger'}`}>
                      {m.api_key_set ? '已设置' : '未设置'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${m.enabled ? 'badge-success' : 'badge-warning'}`}>
                      {m.enabled ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td>
                    <div className="btn-group">
                      <button className="btn btn-outline btn-sm" onClick={() => testModel(m.alias)}>测试</button>
                      <button className="btn btn-outline btn-sm" onClick={() => editModel(m)}>编辑</button>
                      <button className="btn btn-danger btn-sm" onClick={() => deleteModel(m.alias)}>删除</button>
                    </div>
                    {testResult?.alias === m.alias && (
                      <span className={`badge ${testResult.status === 'ok' ? 'badge-success' : 'badge-danger'}`}
                        style={{ marginLeft: 8 }}>
                        {testResult.status === 'testing' ? '...' : testResult.message?.slice(0, 30)}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {models.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>暂无模型，点击"添加模型"开始</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
