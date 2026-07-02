# 排查参考：常用日志与状态命令

以下以 Docker Compose 项目为例；其他项目按实际（如 systemd、pm2、本地进程）替换。

占位符以当前项目的 `docker-compose.yml` 为准：

- `<compose_cmd>`：`docker compose` 或 `docker-compose`
- `<backend_service>`、`<static_service>`：服务名

## 通用（Docker Compose）

| 用途       | 命令 |
|------------|------|
| 后端日志（最近 200 行） | `<compose_cmd> logs --tail=200 <backend_service>` |
| 后端日志（实时）       | `<compose_cmd> logs -f <backend_service>` |
| 静态 / 网关服务日志     | `<compose_cmd> logs --tail=200 <static_service>` |
| 所有服务最近日志       | `<compose_cmd> logs --tail=100` |
| 服务状态               | `<compose_cmd> ps` |

## 占位服务名示例

以下仅为说明：将 `<backend_service>`、`<static_service>` 换成 compose 中的真实名称（常见为 `backend`、`api`、`nginx`、`web` 等）。

- 应用服务：`<compose_cmd> logs --tail=200 <backend_service>` 或 `<compose_cmd> logs -f <backend_service>`
- 静态入口：`<compose_cmd> logs --tail=200 <static_service>`
- 全部服务最近日志：`<compose_cmd> logs --tail=100`
- 确认容器：`<compose_cmd> ps`

## 非 Docker 项目

- 若为本地进程：查看项目文档中的日志路径（如 `logs/`、`/var/log/`）或终端输出。
- 若为 systemd：`journalctl -u <服务名> -n 200 --no-pager`
