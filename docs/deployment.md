# 后端部署说明

## 部署形态

`compose.yaml` 启动三个服务：

- `postgres`：保存家长确认记忆和 LangGraph 会话检查点。
- `api`：启动前自动执行 Alembic 迁移，只在 Compose 内网暴露 `8000`。
- `caddy`：唯一公网入口，开放 `80/443`，自动申请和续期 HTTPS 证书。

公网联调阶段使用 `staging + mock`。健康接口会明确返回 `model_provider=mock`，不会伪装成百炼结果。恢复百炼验证后再切换到 `production + bailian`。

## 服务器准备

服务器需要安装 Docker Engine 和 Docker Compose，并满足：

1. 域名的 A/AAAA 记录已经指向服务器。
2. 防火墙和云安全组允许 TCP `80/443`，需要 HTTP/3 时再允许 UDP `443`。
3. 服务器上的 `80/443` 没有被其他程序占用。

在项目根目录创建部署配置：

```bash
cp .env.example .env
chmod 600 .env
```

至少替换以下值：

```dotenv
POSTGRES_PASSWORD=使用密码生成器生成的随机值
APP_API_TOKEN=另一个独立的随机值
DOMAIN=api.example.com
DEPLOY_ENV=staging
DEPLOY_MODEL_PROVIDER=mock
```

`.env` 已被 Git 忽略，不得提交。`POSTGRES_PASSWORD` 可以包含特殊字符，容器入口会进行 URL 编码。

## 启动和验收

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl https://api.example.com/api/v1/health/live
curl https://api.example.com/api/v1/health/ready
curl https://api.example.com/api/v1/health
```

预期三个容器均为运行状态，API 容器为 `healthy`，三个接口分别返回 `ok`、`ready` 和当前环境信息。

验证鉴权和 Agent 主链路：

```bash
curl -X POST 'https://api.example.com/api/v1/conversations/deploy-check/turns' \
  -H 'Authorization: Bearer 替换为APP_API_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"message":"今天我有一点难过","child":{"child_id":"deploy-check","nickname":"小雨","age":7}}'
```

不带 `Authorization` 的业务请求应返回 `401`。`/health/live` 和 `/health/ready` 不要求令牌，供容器和负载均衡器探测。

## 切换真实模型

完成百炼结构化输出验证后修改 `.env`：

```dotenv
DEPLOY_ENV=production
DEPLOY_MODEL_PROVIDER=bailian
DASHSCOPE_API_KEY=替换为真实密钥
```

然后执行 `docker compose up -d --build`。生产环境缺少 PostgreSQL、服务令牌、百炼模式或百炼密钥时，API 会拒绝启动。

## 运维命令

```bash
# 查看不含儿童原文的结构化 API 日志
docker compose logs -f api

# 升级前备份数据库
docker compose exec -T postgres pg_dump -U childhood_haven childhood_haven > childhood_haven.sql

# 更新代码并重建
git pull --ff-only
docker compose up -d --build

# 停止服务但保留数据卷
docker compose down
```

不要使用 `docker compose down --volumes`，该参数会删除 PostgreSQL 数据卷。升级后应重新检查 readiness、鉴权和一条不含真实儿童信息的测试会话。
