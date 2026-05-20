import { useEffect, useState, useCallback } from 'react'
import { settingsApi } from '../api/settings'
import type { ServerSettings, CodexConfigStatus, ToolStatus } from '../types/settings'

export function useSettings() {
  const [settings, setSettings] = useState<ServerSettings | null>(null)
  const [codexStatus, setCodexStatus] = useState<CodexConfigStatus | null>(null)
  const [toolsStatus, setToolsStatus] = useState<ToolStatus | null>(null)
  const [host, setHost] = useState('127.0.0.1')
  const [port, setPort] = useState(8899)
  const [logLevel, setLogLevel] = useState('info')
  const [loading, setLoading] = useState(false)
  const [codexLoading, setCodexLoading] = useState(false)
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false)

  useEffect(() => {
    settingsApi.getSettings().then((r) => {
      if (r?.server && !r._error) {
        setSettings(r); setHost(r.server.host); setPort(r.server.port); setLogLevel(r.server.log_level)
      }
    })
    settingsApi.getCodexStatus().then((r) => { if (!r._error) setCodexStatus(r as CodexConfigStatus) })
    settingsApi.getTools().then((r) => { if (!r._error) setToolsStatus(r.tools) })
  }, [])

  const portError = (port < 1024 || port > 65535) ? '端口范围: 1024-65535' : ''

  const saveSettings = useCallback(async (): Promise<string | null> => {
    if (portError) return portError
    setLoading(true)
    const r = await settingsApi.updateSettings({ host, port, log_level: logLevel })
    setLoading(false)
    return r._error ? (r._error as string) : null
  }, [host, port, logLevel, portError])

  const refreshCodex = useCallback(async () => {
    const r = await settingsApi.getCodexStatus()
    if (!r._error) setCodexStatus(r as CodexConfigStatus)
  }, [])

  const applyCodex = useCallback(async (): Promise<string | null> => {
    setCodexLoading(true)
    const model = codexStatus?.current_model || 'deepseek-ai/DeepSeek-V3.2'
    const r = await settingsApi.applyCodexConfig(model, port)
    setCodexLoading(false)
    await refreshCodex()
    return r._error ? (r._error as string) : null
  }, [codexStatus, port, refreshCodex])

  const restoreCodex = useCallback(async (): Promise<string | null> => {
    setShowRestoreConfirm(false)
    setCodexLoading(true)
    const r = await settingsApi.restoreCodexConfig()
    setCodexLoading(false)
    await refreshCodex()
    return r._error ? (r._error as string) : null
  }, [refreshCodex])

  const toggleTool = useCallback(async (name: string, enabled: boolean) => {
    await settingsApi.updateTools({ [name]: { enabled } })
    const r = await settingsApi.getTools()
    if (!r._error) setToolsStatus(r.tools)
  }, [])

  return {
    settings, codexStatus, toolsStatus, host, port, logLevel,
    loading, codexLoading, showRestoreConfirm,
    setHost, setPort, setLogLevel, setShowRestoreConfirm,
    portError, saveSettings, applyCodex, restoreCodex, toggleTool, refreshCodex,
  }
}
