import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { modelsApi } from '../api/models'
import type { ProxyStatus } from '../types/status'
import type { ModelEntry } from '../types/model'
import Badge from '../components/Badge'

interface Props { status: ProxyStatus | null }

export default function Dashboard({ status }: Props) {
  const navigate = useNavigate()
  const [models, setModels] = useState<ModelEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadModels = async () => {
    setLoading(true)
    setError('')
    const r = await modelsApi.getModels()
    if (r._error) { setError(r._error); setModels([]) }
    else { setModels(r?.models || []) }
    setLoading(false)
  }

  useEffect(() => { loadModels() }, [])

  const stats = status?.stats
  const enabledModels = models.filter(m => m.enabled)

  return (
    <div>
      <h2 className="card-title" style={{ fontSize: 16, marginBottom: 20 }}>仪表板</h2>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{stats?.request_count ?? 0}</div><div className="stat-label">总请求数</div></div>
        <div className="stat-card"><div className="stat-value" style={{ color: 'var(--success)' }}>{stats?.success_count ?? 0}</div><div className="stat-label">成功</div></div>
        <div className="stat-card"><div className="stat-value" style={{ color: 'var(--danger)' }}>{stats?.error_count ?? 0}</div><div className="stat-label">失败</div></div>
        <div className="stat-card"><div className="stat-value">{stats?.avg_latency_ms?.toFixed(0) ?? 0}ms</div><div className="stat-label">平均延迟</div></div>
        <div className="stat-card"><div className="stat-value">{Math.floor((stats?.uptime_seconds ?? 0) / 60)}m</div><div className="stat-label">运行时间</div></div>
        <div className="stat-card"><div className="stat-value">{enabledModels.length}</div><div className="stat-label">已启用模型</div></div>
      </div>

      <div className="card">
        <h3 className="card-title">已配置模型</h3>
        {loading ? (
          <div className="skeleton">
            {[1, 2, 3].map(i => <div key={i} className="skeleton-row" style={{ height: 36, marginBottom: 8 }} />)}
          </div>
        ) : error ? (
          <div className="error-state">
            <p>{error}</p>
            <button className="btn btn-outline btn-sm" onClick={loadModels}>重试</button>
          </div>
        ) : models.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>暂无模型配置</p>
            <button className="btn btn-primary btn-sm" onClick={() => navigate('/models')}>去配置模型</button>
          </div>
        ) : (
          <div className="table-container">
            <table><thead><tr><th>别名</th><th>目标模型</th><th>提供商</th><th>状态</th></tr></thead>
              <tbody>{models.map((m) => (
                <tr key={m.alias}>
                  <td style={{ fontWeight: 500 }}>{m.alias}</td>
                  <td>{m.target_model}</td>
                  <td>{m.provider || m.adapter}</td>
                  <td><Badge variant={m.enabled ? 'success' : 'warning'}>{m.enabled ? '启用' : '禁用'}</Badge></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
