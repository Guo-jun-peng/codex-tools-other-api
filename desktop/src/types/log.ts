export interface RequestLogEntry {
  timestamp: number
  time: string
  model: string
  endpoint: string
  status_code: number
  elapsed_ms: number
  tokens: number
  error: string
  stream: boolean
  provider: string
  target_model: string
}

export interface StatsSummary {
  uptime_seconds: number
  request_count: number
  success_count: number
  error_count: number
  avg_latency_ms: number
}
