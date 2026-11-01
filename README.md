# dsh-agent-capabilities

DeepSeek Harness 的能力补充包：可配置的图片 API 工作流、独立 HTML 交互图表，以及可选的官方浏览器和桌面控制扩展。

## 范围与来源

本项目自写部分是技能说明、图片 API 适配脚本、图表生成脚本和组合入口。浏览器使用 DeepSeek 官方 Playwright MCP 扩展，桌面控制使用 DeepSeek 官方 Cua Driver 扩展；本项目没有重新实现这两种运行时。依赖由各自上游项目维护并采用各自的许可证。其他社区备用插件及搜索插件不属于本项目，未复制进仓库。

目标版本：DSH **0.2.1-rc.5**、Node.js 24+；Python 脚本要求 Python 3.10+，只使用标准库。其他 DSH 版本尚未验证，不声明通用兼容。

## 安装

在本项目目录打包，然后用 dsh 自带插件管理器安装：

```sh
npm pack --ignore-scripts
dsh plugin --profile desktop add ./dsh-agent-capabilities-1.0.0.tgz
```

CLI/Web 用户将 profile 换成实际名称。遵循宿主的插件安装流程和依赖审批要求。安装路径自动从模块位置解析，无需修改绝对路径。

默认只注册三个技能：`dsh-image-service`、`dsh-visualize`、`dsh-web-desktop`。它们通过 dsh 的普通 shell、技能和工具机制工作，不会自动发送图片请求或操作桌面。

## 图片服务

将 `skills/dsh-image-service/scripts/image-service.example.json` 复制到当前工作区的 `.dsh/image-service.json`，配置完整的 `generationUrl`、可选的 `editUrl`、模型及凭据环境变量名。在本机设置该环境变量，不把密钥写入 Git 或聊天。

```sh
python skills/dsh-image-service/scripts/image_service.py status --config .dsh/image-service.json
python skills/dsh-image-service/scripts/image_service.py generate --prompt "A mountain at sunrise" --output-dir ./generated-images
python skills/dsh-image-service/scripts/image_service.py edit --prompt "Make the sky blue" --image ./input.png --output-dir ./generated-images
```

生成接口采用 JSON 请求，编辑接口采用 multipart；响应须含 `data[].b64_json`。这不是所有供应商的通用适配器；仅返回 URL 或使用不同 API 的服务需要另行适配。未配置真实服务时不能生成图片。服务收费以供应商为准，脚本不自动重试生成请求。

`status` 只做本地配置检查。默认要求 HTTPS，开发用本机 HTTP 服务需显式 `--allow-local`。响应大小、图片数量及文件签名有边界检查；签名检查不是完整图片解码。输出使用随机文件名并拒绝覆盖。

## 交互图表

输入 JSON 示例：

```json
{"title":"Example","labels":["A","B","C"],"values":[12,-3,8]}
```

```sh
python skills/dsh-visualize/scripts/chart.py --input data.json --output chart.html
```

生成无需外部网络资源的 HTML，支持柱状图/折线图切换、悬停详情、数据表和 SVG 导出。输出路径已存在时拒绝覆盖。网站公开部署、Office 编辑与 PDF 导出依靠另选服务或 dsh 已有功能，不属于这个图表脚本的能力。

## 可选浏览器和桌面控制

默认均关闭。可在 profile patch 中覆盖：

```yaml
- id: agent-capabilities
  config:
    enableBrowser: true
    enableDesktop: false
    # executablePath: /path/to/chrome
```

浏览器自动查找常见 Chrome/Edge/Chromium 路径，或使用显式路径。没有找到时交由上游 Playwright 处理安装要求，不自动下载浏览器。它运行独立配置，不继承个人浏览器登录状态。

桌面控制需 `enableDesktop: true`，使用官方本机 SDK。启用前检查宿主支持和系统权限；本项目不修改系统权限。已有同类 provider 时不要重复启用。图片观察需要真实支持图片输入的模型，文本模型应使用可用的结构化信息。新安装的浏览器 provider 不会接管已经活动的会话。

## 验证与限制

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
```

Python 测试使用临时目录及本机模拟 HTTP 服务，不调用付费图片 API。测试覆盖生成/编辑请求、文件保存、凭据缺失、无效响应与 HTML 数据转义。官方 provider 曾在 Windows 的隔离 DSH 实例中通过启动检查；这不等于所有模型、桌面动作或服务的端到端验证。

图片与网页内容属于外部数据。桌面及浏览器输入不是可回滚事务；取消不撤销已经完成的操作。请保留宿主的权限和确认机制。

## License

MIT，见 [LICENSE](LICENSE)。
