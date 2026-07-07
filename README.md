# OEM Manufacturing Platform

Monorepo for OEM company website, Shop member commerce, and Vue admin panel.

## Stack

- `frontend` — Vue 3 public site (default locale: `ko`)
- `admin` — Vue 3 + Element Plus management UI
- `backend` — Django REST Framework API (no Django Admin)
- `mysql`, `redis`, `caddy`

## Quick Start

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up --build
```

3. Open:

- Website: http://localhost/
- Admin: http://localhost/admin/
- API health: http://localhost/api/health

### 局域网访问（同 WiFi / 同网段设备）

1. 查本机 IP（Windows PowerShell）：

```powershell
ipconfig
```

找到当前网络的 **IPv4 地址**（如 `192.168.1.100`）。

2. 确保 Docker Desktop 已启动，且本项目 `docker compose up` 正在运行。

3. 其他设备浏览器访问：

- 官网：`http://<本机IP>/`（例：`http://192.168.1.100/`）
- 管理后台：`http://<本机IP>/admin/`

4. 若无法访问，请检查：

- Windows 防火墙是否放行 **80 端口**（或临时关闭防火墙测试）
- 访问设备与电脑是否在同一局域网
- `.env` 中 `VITE_API_BASE_URL=/api`（不要用 `http://localhost/api`）

修改 `.env` 或 `docker-compose.yml` 后需重启：

```bash
docker compose up -d --force-recreate frontend admin caddy backend
```

## Default Accounts

- Admin: `admin@oem.co` / `Admin123!`
- Shop member: register via `/shop/register`

## Development

- Backend only: `cd backend && pip install -r requirements.txt`
- Frontend: `cd frontend && npm install && npm run dev`
- Admin: `cd admin && npm install && npm run dev`

## Project Spec

See [MASS CONNECTED 平台文档.md](MASS%20CONNECTED%20%E5%B9%B3%E5%8F%B0%E6%96%87%E6%A1%A3.md) and the requirement docs under `project/`.

**Feature modules (examples)**:

- Simple quote (`/simple-quote`): injection, 3D print, PCB, software, IC
- **Paper box generator** (`/packaging/box`): FEFCO dieline preview + `paper_box` auto quote (see `project/纸盒包装生成器方案书 V1.0.md`)
