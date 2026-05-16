const zh: Record<string, string> = {
  appTitle: 'Codex 国内模型适配工具',
  dashboard: '仪表板',
  models: '模型配置',
  settings: '全局设置',
  logs: '监控日志',
  about: '关于',

  proxyStatus: '代理状态',
  running: '运行中',
  stopped: '已停止',
  uptime: '运行时间',
  requests: '请求数',
  success: '成功',
  errors: '错误',
  avgLatency: '平均延迟',
  version: '版本',

  modelAlias: '模型别名',
  targetModel: '目标模型',
  provider: '提供商',
  adapter: '适配器',
  baseUrl: 'API 地址',
  apiKey: 'API Key',
  apiKeyEnv: '环境变量',
  enabled: '启用',
  isMultimodal: '多模态',
  testConn: '测试连接',
  addModel: '添加模型',
  deleteModel: '删除',
  saveModel: '保存',

  serverConfig: '服务器配置',
  host: '监听地址',
  port: '端口',
  logLevel: '日志级别',
  autoStart: '自动启动',
  closeToTray: '关闭窗口最小化到托盘',

  codexConfig: 'Codex 配置管理',
  detectCodexDir: '检测目录',
  applyCodexConfig: '写入配置',
  restoreCodexConfig: '恢复默认',
  configFound: '已找到',
  configNotFound: '未找到',
  backupExists: '备份存在',
  noBackup: '无备份',

  importConfig: '导入配置',
  exportConfig: '导出配置',
  shutdown: '关闭代理',

  tools: '服务端工具',
  webSearch: '网页搜索',
  webSearchDesc: '自动执行 DuckDuckGo 搜索',

  testSuccess: '连接成功',
  testFail: '连接失败',
}

let lang = 'zh'

export function t(key: string): string {
  return zh[key] || key
}

export function setLang(l: string) {
  lang = l
}
