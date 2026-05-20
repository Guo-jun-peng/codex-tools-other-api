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
