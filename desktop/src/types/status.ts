export interface ProxyStatus {
  running: boolean
  host: string
  port: number
  version: string
  stats: {
    uptime_seconds: number
    request_count: number
    success_count: number
    error_count: number
    avg_latency_ms: number
  }
}
