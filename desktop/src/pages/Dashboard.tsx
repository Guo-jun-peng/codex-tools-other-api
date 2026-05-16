import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface Props {
  status: any
}

export default function Dashboard({ status }: Props) {
  const [models, setModels] = useState<any[]>([])

  useEffect(() => {
    api.getModels().then((r) => setModels(r?.models || []))
  }, [])

  const stats = status?.stats
  const enabledModels = models.filter((m: any) => m.enabled)

  return (
    <div>
      <h2 className="card-title" style={{ fontSize: 16, marginBottom: 20 }}>仪表板</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.request_count ?? 0}</div>
          <div className="stat-label">总请求数</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--success)' }}>{stats?.success_count ?? 0}</div>
          <div className="stat-label">成功</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--danger)' }}>{stats?.error_count ?? 0}</div>
          <div className="stat-label">失败</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.avg_latency_ms?.toFixed(0) ?? 0}ms</div>
          <div className="stat-label">平均延迟</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{Math.floor((stats?.uptime_seconds ?? 0) / 60)}m</div>
          <div className="stat-label">运行时间</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{enabledModels.length}</div>
          <div className="stat-label">已启用模型</div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">已配置模型</h3>
        {models.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>暂无模型配置，请在"模型配置"页面添加</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>别名</th>
                  <th>目标模型</th>
                  <th>提供商</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m: any) => (
                  <tr key={m.alias}>
                    <td style={{ fontWeight: 500 }}>{m.alias}</td>
                    <td>{m.target_model}</td>
                    <td>{m.provider || m.adapter}</td>
                    <td>
                      <span className={`badge ${m.enabled ? 'badge-success' : 'badge-warning'}`}>
                        {m.enabled ? '启用' : '禁用'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
