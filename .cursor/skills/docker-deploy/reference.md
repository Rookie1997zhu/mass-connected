# Docker 部署参考（通用占位）

以下命令中的服务名、目录、端口均以**当前仓库**的 `docker-compose.yml`（或 `docker-compose.yaml`）与 README / DEPLOY 为准。请先将占位符替换为探测得到的值：

- `<repo_root>`：克隆后的项目根目录
- `<frontend_dir>`、`<build_cmd>`、`<compose_cmd>`、`<static_service>`、`<backend_service>`、`<db_service>`

## 环境要求

- Docker Desktop、Docker Compose
- 若需本地构建前端：Node.js + Yarn 或 npm

## 首次部署（模板）

```bash
git clone <repository-url>
cd <repo_root>
# 按项目文档配置 .env 或 compose 环境变量
<compose_cmd> up -d --build
# 若前端需在宿主机构建，再执行「前端更新部署」模板
<compose_cmd> restart <static_service>
```

## 日常操作（模板）

```bash
<compose_cmd> up -d
<compose_cmd> down
<compose_cmd> ps
<compose_cmd> logs -f
<compose_cmd> logs -f <backend_service>
<compose_cmd> logs -f <static_service>
```

## 前端更新部署（模板）

```bash
cd <frontend_dir>
<build_cmd>
cd <repo_root>
<compose_cmd> restart <static_service>
```

## 后端更新部署（模板）

```bash
<compose_cmd> restart <backend_service>
```

## 数据库与应用命令（模板）

```bash
# 数据库客户端以镜像与文档为准，示例：
<compose_cmd> exec <db_service> <db_client_cmd>

# 应用内命令示例（按栈替换）：
<compose_cmd> exec <backend_service> python manage.py migrate
```

## 端口与访问地址

Compose 中映射的端口因项目而异，请用 `docker compose ps` 或 compose 文件中的 `ports:` 确认，勿假设固定端口号。

## 常见问题

- 前端不生效：重新 build → 重启静态服务 → 浏览器 Ctrl+F5
- 清空重来：`<compose_cmd> down -v`，再 `<compose_cmd> up -d --build`
- 资源占用：`docker stats`
