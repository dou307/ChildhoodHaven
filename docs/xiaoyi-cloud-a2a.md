# 小艺云 A2A 接入

童心译站保留 HarmonyOS 应用内入口，同时由同一套 FastAPI/LangGraph Agent 提供小艺云 A2A 入口。

```text
HarmonyOS 应用 -> /api/v1/conversations/{id}/turns -> LangGraph
小艺 Client Agent -> /api/v1/a2a -> JSON-RPC/SSE 适配 -> LangGraph
```

## 当前实现

- 单一 HTTPS Endpoint：`POST /api/v1/a2a`
- 通信格式：JSON-RPC 2.0
- 对话方法：`message/stream`
- 流式传输：`Content-Type: text/event-stream`
- 会话控制：`tasks/cancel`、`clearContext`
- 认证：复用 `APP_API_TOKEN`，在小艺开放平台选择 Header 认证并配置
  `Authorization: Bearer <APP_API_TOKEN>`
- 会话维持：选择服务器间无状态通信；用户对话上下文仍按请求中的 `sessionId` 保存

小艺的原始 `sessionId` 会先经过 SHA-256 生成内部会话和儿童标识，不直接写入业务路径。
小艺入口暂时使用“昵称为小朋友、年龄为 6 岁”的中性档案。完成家长账号授权前，不把小艺会话
与应用内儿童档案或家长确认记忆合并，避免不同身份之间误关联。

## 小艺开放平台配置

创建“云 A2A 模式”Agent，并填写：

| 配置项 | 值 |
| --- | --- |
| API URL | `https://<正式域名>/api/v1/a2a` |
| 会话维持方式 | 服务器间无状态通信 |
| 认证方式 | Header |
| Header 名称 | `Authorization` |
| Header 值 | `Bearer <APP_API_TOKEN>` |

第一阶段只返回 Markdown 文本，不绑定小艺卡片。卡片输出需要先在平台创建卡片，再按照平台生成的
`cardName` 和字段结构返回 `cardsInfo`，不能在代码中提前猜测。

## 本地协议检查

```powershell
$body = @{
  jsonrpc = "2.0"
  id = "rpc-1"
  method = "message/stream"
  params = @{
    id = "task-1"
    sessionId = "demo-session"
    message = @{
      role = "user"
      parts = @(@{ kind = "text"; text = "我今天有一点难过" })
    }
  }
} | ConvertTo-Json -Depth 8

Invoke-WebRequest `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/a2a" `
  -ContentType "application/json" `
  -Body $body
```

公网部署时增加 `Authorization` Header，并确认代理没有缓冲 SSE。Caddy 当前直接反向代理该接口，
应用响应还会显式返回 `X-Accel-Buffering: no`。

## 尚待平台联调

- 小艺开放平台真实请求和鉴权 Header 是否成功到达服务端
- SSE 事件在小艺客户端的文字与任务状态呈现
- 小艺卡片输出配置
- 华为账号授权及家长账户绑定
- 端侧插件或意图框架调用应用内功能

协议依据：

- https://developer.huawei.com/consumer/cn/doc/service/cloud-a2a-0000002640266052
- https://developer.huawei.com/consumer/cn/doc/service/agent2agent-comments-0000002500412353
- https://developer.huawei.com/consumer/cn/doc/service/message-stream-0000002505761434
