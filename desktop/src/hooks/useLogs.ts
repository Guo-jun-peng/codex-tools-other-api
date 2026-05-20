import { useEffect, useState, useRef, useCallback } from 'react'
import { logsApi } from '../api/logs'
import type { RequestLogEntry } from '../types/log'

export function useLogs() {
  const [logs, setLogs] = useState<RequestLogEntry[]>([])
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
        const entry = JSON.parse(event.data) as RequestLogEntry
        setLogs((prev) => [entry, ...prev].slice(0, 200))
      } catch {}
    }
  }, [reconnectDelay])

  useEffect(() => {
    logsApi.getLogs(50).then((r) => { if (!r._error) setLogs(r?.logs || []) })
    connect()
    return () => {
      wsRef.current?.close()
      clearTimeout(reconnectTimerRef.current)
    }
  }, [])

  const clearLogs = useCallback(async () => {
    await logsApi.clearLogs()
    setLogs([])
  }, [])

  return { logs, connected, reconnectDelay, clearLogs, connect }
}
