export interface ModelEntry {
  alias: string
  target_model: string
  provider: string
  adapter: string
  base_url: string
  api_key_env: string
  api_key_set: boolean
  api_key_hint?: string
  enabled: boolean
  is_multimodal: boolean
  vision_alias: string
  is_image_gen: boolean
  image_gen_alias: string
  is_video_gen: boolean
  video_gen_alias: string
  available_adapters: string[]
}

export interface ModelForm {
  alias: string
  target_model: string
  provider: string
  adapter: string
  base_url: string
  api_key: string
  api_key_env: string
  enabled: boolean
}

export interface AdapterInfo {
  name: string
  base_url: string
  api_key_env: string
}

export interface AdapterDefaults {
  base_url: string
  api_key_env: string
}

export interface TestResult {
  status: 'ok' | 'error' | 'testing'
  elapsed_ms?: number
  message: string
}
