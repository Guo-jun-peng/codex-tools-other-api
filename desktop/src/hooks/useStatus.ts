import { useEffect, useState, useCallback } from 'react'
import { statusApi } from '../api/status'
import type { ProxyStatus } from '../types/status'

const POLL_INTERVAL_MS = 5000

export function useStatus() {
  const [status, setStatus] = useState<ProxyStatus | null>(null)

  const poll = useCallback(async () => {
    const r = await statusApi.getStatus()
    if (!r._error) setStatus(r as ProxyStatus)
    else setStatus(null)
  }, [])

  useEffect(() => {
    poll()
    const timer = setInterval(poll, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [poll])

  return status
}
