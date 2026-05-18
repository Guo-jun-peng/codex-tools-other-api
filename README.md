# Codex 国内模型适配工具

将 OpenAI Responses API 转换为 Chat Completions API 的本地代理，使 [Codex CLI](https://github.com/openai/codex) 无缝接入国产大模型。

支持 **6 个国产模型平台**，提供 **Electron + React 桌面管理界面**，一键配置、自动管理 Codex 配置。

## 支持的平台

| 平台 | 适配器 | API 地址 | 环境变量 |
|------|--------|----------|----------|
| SiliconFlow (硅基流动) | `siliconflow` | `https://api.siliconflow.cn/v1` | `SILICONFLOW_API_KEY` |
| 通义千问 (阿里云) | `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `QWEN_API_KEY` |
| DeepSeek 官方 | `deepseek` | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` |
| Kimi (Moonshot) | `kimi` | `https://api.moonshot.cn/v1` | `KIMI_API_KEY` |
| 豆包 (火山引擎) | `doubao` | `https://ark.cn-beijing.volces.com/api/v3` | `ARK_API_KEY` |
| 智谱 GLM | `zhipu` | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |

## 功能特性

- **协议转换**：OpenAI Responses API ↔ Chat Completions API 双向转换，支持 SSE 流式输出
- **工具代理循环**：内置 `web_search` 工具（DuckDuckGo），Codex 可发起联网搜索
- **桌面管理界面**：Electron + React 桌面应用，系统托盘驻留
- **模型配置管理**：可视化添加/编辑/删除/启用/停用模型，连接测试
- **Codex 配置管理**：自动检测并修改 `~/.codex/config.toml`，支持备份恢复
- **视觉模型路由**：自动检测图片输入，路由到视觉模型
- **日志监控**：实时 WebSocket 推送日志，请求统计
- **静默启动**：Windows 下通过 VBScript 完全隐藏命令行窗口

## 快速开始

### 环境要求

- **Python** >= 3.10
- **Node.js** >= 18
- **Git Bash** 或 WSL（Windows 下推荐）

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖（仅开发/打包桌面端时需要）
cd desktop && npm install && cd ..
```

### 2. 配置 API Key

```bash
# 复制环境变量模板
cp example.env .env

# 编辑 .env，填入你使用的平台 API Key
# 至少配置一个平台的 Key，例如：
# SILICONFLOW_API_KEY=sk-your-real-key
```

### 3. 启动代理

**命令行方式：**

```bash
python -m codex_adapter_bridge.cli start --port 8899
```

**桌面应用方式（Windows）：**

```bash
# 运行桌面管理界面
cd desktop && npx electron .
```

### 4. 配置模型

打开浏览器访问 `http://127.0.0.1:8899`，进入**模型配置**页面，点击"添加模型"：

- **平台**：选择适配器（如 `siliconflow`），自动填充提供商、API 地址、环境变量
- **模型别名**：Codex 中使用的名称（如 `gpt-5-code`）
- **目标模型**：上游模型 ID（如 `deepseek-ai/DeepSeek-V3.2`）
- **API Key**：填入对应平台的 API Key（编辑时显示脱敏值如 `sk-a***789`，留空则保留原 Key）

模型配置支持：
- **启用/停用切换**：点击状态开关临时停用模型，无需删除
- **连接测试**：点击"测试"验证配置是否正确
- **编辑时 Key 保护**：编辑已配置模型时 API Key 显示为脱敏提示，修改才更新

### 5. 配置 Codex

在**仪表板**或**设置**页面，点击"写入 Codex 配置"。工具会自动：
1. 备份 `~/.codex/config.toml` 和 `~/.codex/auth.json`
2. 写入自定义 provider 配置，指向本地代理
3. 重启 Codex 即可使用

手动配置方式：编辑 `~/.codex/config.toml`：

```toml
model_provider = "custom"
model = "gpt-5-code"

[model_providers.custom]
name = "Codex适配"
base_url = "http://127.0.0.1:8899/v1"
wire_api = "responses"
requires_openai_auth = true
```

> API Key 通过 Codex 的 `auth.json` 自动传入代理，无需在 `config.toml` 中配置。

## 命令行

```bash
# 启动代理
python -m codex_adapter_bridge.cli start --port 8899

# 生成默认配置文件
python -m codex_adapter_bridge.cli init

# 仅修改 Codex 配置（不启动代理）
python -m codex_adapter_bridge.cli codex apply --model gpt-5-code

# 恢复 Codex 原始配置
python -m codex_adapter_bridge.cli codex restore
```

## 项目结构

```
codex-bat/
├── codex_adapter_bridge/       # Python 后端
│   ├── server.py               # FastAPI 主应用，/v1/responses 端点
│   ├── admin_api.py            # 管理 API（模型 CRUD、设置、日志）
│   ├── config.py               # YAML 配置管理（热加载）
│   ├── protocol.py             # Responses ↔ Chat 协议转换
│   ├── client.py               # 上游 HTTP 客户端
│   ├── tools.py                # 服务端工具代理（web_search）
│   ├── codex_config.py         # Codex config.toml 管理
│   ├── middleware.py            # 请求日志、错误处理
│   ├── stats.py                # 请求统计
│   ├── cli.py                  # 命令行入口
│   ├── adapters/               # 6 个平台适配器
│   │   ├── base.py             #   基类
│   │   ├── siliconflow.py      #   SiliconFlow
│   │   ├── qwen.py             #   通义千问
│   │   ├── deepseek.py         #   DeepSeek
│   │   ├── kimi.py             #   Kimi
│   │   ├── doubao.py           #   豆包
│   │   └── glm.py              #   智谱 GLM
│   └── models.py               # 数据模型（Responses API 格式）
├── desktop/                    # 前端桌面应用
│   ├── electron/main.js        # Electron 主进程
│   ├── src/
│   │   ├── App.tsx             # React 根组件
│   │   ├── pages/              # 页面
│   │   │   ├── Dashboard.tsx   #   仪表板
│   │   │   ├── Models.tsx      #   模型配置
│   │   │   ├── Settings.tsx    #   设置
│   │   │   └── Logs.tsx        #   日志
│   │   └── services/api.ts     # API 客户端
│   └── dist/                   # 构建产物
├── config.yaml                 # 代理配置文件
├── start.vbs                   # Windows 静默启动脚本
├── create_shortcut.py          # 桌面快捷方式创建
├── example.env                 # 环境变量模板
├── requirements.txt            # Python 依赖
└── pyproject.toml              # 项目元数据
```

## 管理 API

桌面管理界面通过以下 API 与代理通信：

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/admin/api/status` | 代理运行状态 |
| `GET` | `/admin/api/models` | 列出已配置模型 |
| `POST` | `/admin/api/models` | 添加模型 |
| `PUT` | `/admin/api/models/{alias}` | 编辑模型 |
| `DELETE` | `/admin/api/models/{alias}` | 删除模型 |
| `PUT` | `/admin/api/models/{alias}/toggle` | 启用/停用模型 |
| `POST` | `/admin/api/models/{alias}/test` | 测试模型连接 |
| `GET` | `/admin/api/adapters` | 列出可用适配器 |
| `GET` | `/admin/api/settings` | 获取全局设置 |
| `PUT` | `/admin/api/settings` | 更新全局设置 |
| `GET` | `/admin/api/logs` | 获取请求日志 |
| `WS` | `/admin/api/logs/stream` | WebSocket 实时日志 |
| `POST` | `/admin/api/codex/apply` | 写入 Codex 配置 |
| `POST` | `/admin/api/codex/restore` | 恢复 Codex 配置 |
| `POST` | `/admin/api/shutdown` | 关闭代理 |

## 配置说明

`config.yaml` 结构：

```yaml
server:
  host: 127.0.0.1
  port: 8899

providers:
  siliconflow:                    # 平台名称
    adapter: siliconflow          #   适配器名
    base_url: https://api.siliconflow.cn/v1
    api_key_env: SILICONFLOW_API_KEY  # 从环境变量读取 Key
    enabled: true

model_mapping:
  gpt-5-code:                     # Codex 中使用的别名
    target: deepseek-ai/DeepSeek-V3.2   # 上游模型 ID
    provider: siliconflow
    enabled: true
```

- `api_key` 通过环境变量注入，不会写入 `config.yaml`
- 带有 `/` 的模型名（如 `deepseek-ai/DeepSeek-V3.2`）自动路由到 SiliconFlow
- 支持模型别名配置 `vision_alias`（视觉模型）、`image_gen_alias`（生图模型）

## 开发

```bash
# 启动前端开发服务器
cd desktop && npm run dev

# 构建前端
cd desktop && npm run build

# 启动 Electron 桌面应用
cd desktop && npm start
```

## 致谢

本项目参考了 [codex-cn-bridge](https://github.com/git-liu835/codex-cn-bridge) (MIT License) 的协议转换思路。

## License

MIT
