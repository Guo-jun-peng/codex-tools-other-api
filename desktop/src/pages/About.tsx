export default function About() {
  return (
    <div>
      <h2 className="card-title" style={{ fontSize: 16, marginBottom: 20 }}>关于</h2>
      <div className="card about-section">
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Codex 国内模型适配工具</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
          版本 1.0.0
        </p>

        <p>
          将 OpenAI Responses API 转换为 Chat Completions API 的本地代理工具，
          使 Codex CLI、桌面端、VS Code 插件无缝接入国产大模型。
        </p>

        <h3 style={{ fontSize: 14, fontWeight: 600, marginTop: 24, marginBottom: 12 }}>支持的模型提供商</h3>
        <ul style={{ paddingLeft: 20, fontSize: 13, lineHeight: 2, color: 'var(--text-secondary)' }}>
          <li>SiliconFlow (硅基流动) — DeepSeek, Qwen, GLM 系列</li>
          <li>通义千问 (Qwen) — 阿里云 DashScope</li>
          <li>DeepSeek 官方 API</li>
          <li>Kimi (Moonshot)</li>
          <li>豆包 (火山引擎 Ark)</li>
          <li>智谱 GLM</li>
        </ul>

        <h3 style={{ fontSize: 14, fontWeight: 600, marginTop: 24, marginBottom: 12 }}>使用方法</h3>
        <ol style={{ paddingLeft: 20, fontSize: 13, lineHeight: 2.2, color: 'var(--text-secondary)' }}>
          <li>在"模型配置"页面添加模型并设置 API Key</li>
          <li>代理自动启动在 http://localhost:8899</li>
          <li>在"全局设置"中点击"写入配置"自动配置 Codex</li>
          <li>或在终端设置: export OPENAI_BASE_URL="http://localhost:8899/v1"</li>
        </ol>

        <p style={{ marginTop: 24, fontSize: 12, color: 'var(--text-secondary)' }}>
          基于 open-source 项目构建 | MIT License
        </p>
      </div>
    </div>
  )
}
