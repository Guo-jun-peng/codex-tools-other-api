import { useEffect, useState, useRef, useCallback } from 'react'
import { api } from '../services/api'

export default function Logs() {
  const [logs, setLogs] = useState<any[]>([])
  const [connected, setConnected] = useState(false)
  const [reconnectDelay, setReconnectDelay] = useState(1)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<any>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/admin/api/logs/stream`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => { setConnected(true); setReconnectDelay(1) }
    ws.onclose = () => {
      setConnected(false)
      const delay = Math.min(reconnectDelay * 1000, 30000)
      reconnectTimerRef.current = setTimeout(() => {
        setReconnectDelay(prev => Math.min(prev * 2, 30))
        connect()
      }, delay)
    }
    ws.onerror = () => { ws.close() }
    ws.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data)
        setLogs((prev) => [entry, ...prev].slice(0, 200))
      } catch {}
    }
  }, [reconnectDelay])

  useEffect(() => {
    api.getLogs(50).then((r) => { if (!r._error) setLogs(r?.logs || []) })
    connect()
    return () => {
      wsRef.current?.close()
      clearTimeout(reconnectTimerRef.current)
    }
  }, [])

  const clearLogs = async () => { await api.clearLogs(); setLogs([]) }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="card-title" style={{ fontSize: 16, margin: 0 }}>监控日志</h2>
        <div className="btn-group">
          <span className={`badge ${connected ? 'badge-success' : 'badge-danger'}`} style={{ marginRight: 8 }}>
            {connected ? '实时连接' : `重连中(${reconnectDelay}s)`}
          </span>
          <button className="btn btn-outline btn-sm" onClick={clearLogs}>清空</button>
          {!connected && <button className="btn btn-outline btn-sm" onClick={connect}>手动连接</button>}
        </div>
      </div>
      <div className="card" style={{ maxHeight: 'calc(100vh - 180px)', overflow: 'auto', padding: 0 }}>
        {logs.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>暂无请求日志</div>
        ) : logs.map((log: any, i: number) => (
          <div key={i} className={`log-line ${log.status_code >= 400 ? 'error' : ''}`}>
            <span style={{ color: 'var(--text-secondary)', marginRight: 10 }}>{log.time}</span>
            <span style={{ fontWeight: 500, marginRight: 8 }}>{log.endpoint}</span>
            <span className={`badge ${log.status_code < 400 ? 'badge-success' : 'badge-danger'}`} style={{ marginRight: 8 }}>{log.status_code}</span>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>{log.elapsed_ms}ms</span>
            <span style={{ color: 'var(--text-secondary)', marginRight: 8 }}>{log.provider}/{log.target_model}</span>
            {log.error && <span style={{ color: 'var(--danger)' }}>{log.error.slice(0, 80)}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
