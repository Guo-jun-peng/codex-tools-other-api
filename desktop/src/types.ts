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

export interface ModelEntry {
  alias: string
  target_model: string
  provider: string
  adapter: string
  base_url: string
  api_key_env: string
  api_key_set: boolean
  enabled: boolean
  is_multimodal: boolean
  vision_alias: string
  is_image_gen: boolean
  image_gen_alias: string
  is_video_gen: boolean
  video_gen_alias: string
  available_adapters: string[]
}

export interface ServerSettings {
  server: {
    host: string
    port: number
    log_level: string
    auto_start: boolean
    close_to_tray: boolean
  }
  config_path: string
}

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

export interface CodexConfigStatus {
  found: boolean
  dir: string
  has_backup: boolean
  config_exists: boolean
  current_model: string
  current_port: string
}

export interface ToolStatus {
  [name: string]: {
    enabled: boolean
  }
}
