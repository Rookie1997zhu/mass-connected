# 聊天 WebSocket 容量与扩展

## 目标

同时在线 WebSocket 连接 **≥ 1 万**，可水平扩展到数万。

## 架构要点

- `backend`：HTTP API（REST 发消息、历史、纠纷）
- `chat-ws`：仅 WebSocket；Compose 可 `docker compose up --scale chat-ws=N`
- Redis DB2：Channels；DB0：cache/未读；DB1：Celery
- 每用户 1 条长连接，推送 `chat.user.{id}`，无一对多广播大群

## 副本估算

```
R ≈ ceil(N / C)
```

- `N`：目标同时在线连接数
- `C`：单 `chat-ws` 副本在目标机型上的舒适连接数（压测标定，经验预留 **2000～5000**）

示例：N=10000，C=2500 → R=4。

## 压测

```bash
# 需安装 websockets，并提供有效 access JWT
pip install websockets
python backend/scripts/chat_ws_baseline.py \
  --url ws://localhost/ws/chat/ \
  --token "$ACCESS_TOKEN" \
  --connections 200 \
  --hold 5
```

生产前按目标机型将 `--connections` 提升至单副本目标 C，再验证多副本近似线性。

## 运维注意

- 容器 `ulimits.nofile` 已设为 65535
- Caddy `/ws/*` → `chat-ws:8001`
- 发送限流默认 30 条/分钟/用户（`CHAT_RATE_LIMIT_PER_MINUTE`）
