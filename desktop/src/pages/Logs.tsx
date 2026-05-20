import { useLogs } from '../hooks/useLogs'
import Badge from '../components/Badge'

export default function Logs() {
  const { logs, connected, reconnectDelay, clearLogs, connect } = useLogs()

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="card-title" style={{ fontSize: 16, margin: 0 }}>监控日志</h2>
        <div className="btn-group">
          <Badge variant={connected ? 'success' : 'danger'} style={{ marginRight: 8 }}>
            {connected ? '实时连接' : `重连中(${reconnectDelay}s)`}
          </Badge>
          <button className="btn btn-outline btn-sm" onClick={clearLogs}>清空</button>
          {!connected && <button className="btn btn-outline btn-sm" onClick={connect}>手动连接</button>}
        </div>
      </div>
      <div className="card" style={{ maxHeight: 'calc(100vh - 180px)', overflow: 'auto', padding: 0 }}>
        {logs.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>暂无请求日志</div>
        ) : logs.map((log, i) => (
          <div key={i} className={`log-line ${log.status_code >= 400 ? 'error' : ''}`}>
            <span style={{ color: 'var(--text-secondary)', marginRight: 10 }}>{log.time}</span>
            <span style={{ fontWeight: 500, marginRight: 8 }}>{log.endpoint}</span>
            <Badge variant={log.status_code < 400 ? 'success' : 'danger'} style={{ marginRight: 8 }}>{log.status_code}</Badge>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>{log.elapsed_ms}ms</span>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>{log.provider}/{log.target_model}</span>
            {log.error && <span style={{ color: 'var(--danger)' }}>{log.error.slice(0, 80)}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
