# 童心驿站 Agent

面向 3-8 岁儿童及其家长的情绪陪伴 Agent。项目当前正在从概念验证网页重构为可解释、可测试、可持续会话的标准 Agent 系统。

## 当前阶段

当前已实现文本、语音和朗读主链路的源码闭环：

1. 对儿童输入进行安全分级。
2. 结构化理解事件、情绪和缺失信息。
3. Agent 决定追问、生成绘本或请求监护人介入。
4. 按决策调用故事和家长建议工具。
5. 返回完整工具轨迹，便于演示和评测。
6. 仅在家长确认后保存长期记忆，并支持跨会话读取和删除。
7. HarmonyOS 端采集 16 kHz 单声道音频，调用离线中文语音识别，并允许发送前修改文字。
8. HarmonyOS 端支持逐页离线 TTS 朗读，以及记忆候选确认、列表刷新和删除。
9. 单个 HAP 内提供儿童模式和 PIN 保护的家长模式，儿童档案在本机持久化。
10. 会话绑定儿童身份，并使用 `turn_id` 防止网络重试重复执行同一轮。
11. 使用 Alembic 管理业务表，并通过 PostgreSQL 持久化长期记忆和 LangGraph 检查点。
12. 输出不含儿童原文的结构化请求与 Agent 节点耗时、状态和错误类型日志。
13. 提供小艺云 A2A JSON-RPC/SSE 适配入口，与 HarmonyOS 应用复用同一套 Agent 大脑。

`mock` 模式只用于本地开发和自动化测试，所有响应都会明确标注模型模式。系统不会在百炼调用失败后静默返回伪造结果。

## 本地运行

```powershell
cd backend
uv sync --extra dev
Copy-Item ..\.env.example ..\.env
uv run uvicorn app.main:app --reload --port 8000 --no-access-log
```

访问：

- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- OpenAPI：`http://127.0.0.1:8000/docs`
- 小艺云 A2A：`POST http://127.0.0.1:8000/api/v1/a2a`

百炼真实调用与结构化输出联调按当前安排暂缓。后续启用时，在根目录 `.env` 中设置：

```dotenv
MODEL_PROVIDER=bailian
DASHSCOPE_API_KEY=your-key
```

API Key 不得提交到 Git。

生产部署还必须设置 `DATABASE_URL`、`APP_API_TOKEN` 和 `POSTGRES_PASSWORD`。开发模式可以使用内存存储；生产模式缺少百炼、PostgreSQL 或 API 访问令牌配置时会拒绝启动。

使用 PostgreSQL 时，启动应用前执行迁移：

```powershell
cd backend
$env:DATABASE_URL = "postgresql://user:password@127.0.0.1:5432/childhood_haven"
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000 --no-access-log
```

后端 Docker 镜像会在入口阶段自动执行 `alembic upgrade head`。结构化日志仅包含请求 ID、路由模板、状态码、Agent 节点名、耗时和错误类型，不记录儿童输入、昵称、记忆内容或路径中的实际 ID。

公网联调使用 Caddy 作为唯一入口，API 端口不会直接发布到宿主机。当前可先用明确标识的 `staging + mock` 部署，百炼联调完成后再切换 `production + bailian`：

```powershell
Copy-Item .env.example .env
# 修改 .env 中的 POSTGRES_PASSWORD、APP_API_TOKEN 和 DOMAIN
docker compose up -d --build
```

完整服务器准备、HTTPS 验收、备份和升级命令见 `docs/deployment.md`。

## 测试

```powershell
cd backend
uv run pytest
uv run python scripts/smoke_e2e.py
```

冒烟脚本需要本地 API 已在 `8000` 端口运行，会实际检查健康状态、Agent 会话、幂等重试、记忆确认/删除和会话归属冲突。

HarmonyOS 构建：

```powershell
cd harmony
.\hvigorw.bat --mode module -p product=default -p module=entry@default assembleHap --no-daemon
```

首次在另一台电脑打开时，由 DevEco Studio 更新 `local.properties` 中的 SDK 和 Node.js 路径。客户端地址统一配置在 `harmony/entry/build-profile.json5` 的 `API_BASE_URL` 字段。真机联调前需将它改为公网 HTTPS 后端地址，并在 DevEco Studio 中配置签名。`127.0.0.1` 在真机上指向手机本身，不能访问电脑上的后端。

构建配置中的 `API_TOKEN` 仅是空的复赛联调占位，不得提交真实令牌。把固定令牌写入安装包不适合正式发布；公开上线前应换成家长账户登录和服务端签发的短期访问令牌。Release 构建会拒绝使用非 HTTPS 地址。

## 当前验证边界

- 已验证：30 个后端测试、严格 checkpoint 反序列化、Docker PostgreSQL 跨重启持久化、后端镜像自动迁移启动、本地 Caddy HTTPS staging 全栈、真实 HTTP 冒烟请求、GitHub Actions CI、HarmonyOS 6.1.1(24) ArkTS 编译和未签名 HAP 打包。
- 已编译但尚未真机验证：麦克风采集、离线中文识别、逐页离线 TTS、家长确认/查看/删除记忆界面。
- 尚未验证：真实百炼 API 输出、HarmonyOS 真机安装和真实域名的公网 HTTPS 联调。
- 尚未实现：家长身份认证、主动回访、绘本插画素材与朗读同步高亮。

架构和复赛范围见 `docs/architecture.md`，小艺双入口配置见 `docs/xiaoyi-cloud-a2a.md`，
一个月执行安排见 `docs/roadmap.md`。
