---
name: docker-deploy
description: 通用 Docker / Docker Compose 部署与运维。用户说修改完前端或后端代码、需要更新部署时，按本技能执行相应命令。也用于首次部署、启停、日志、数据库、排错。适用于任何 Docker Compose 项目。
---

# Docker 部署（通用）

## 项目参数（先识别再执行）

先从 `docker-compose.yml`、README/DEPLOY 文档识别以下参数；未识别到则先询问用户：

- `<frontend_dir>`：前端目录（如 `frontend`）
- `<compose_cmd>`：`docker compose` 或 `docker-compose`
- `<static_service>`：静态服务（如 `nginx` / `web`）
- `<backend_service>`：后端服务（如 `backend` / `api`）
- `<db_service>`：数据库服务（如 `db` / `mysql` / `postgres`）

执行命令时统一使用这些参数位，避免把某一具体项目的服务名硬编码到别的仓库。

### 自动探测流程（必须先做）

1. 读取 `docker-compose.yml`（或 `docker-compose.yaml`）：
   - 识别 `<compose_cmd>`：优先 `docker compose`，失败回退 `docker-compose`。
   - 识别服务名：根据 `services:` 下名称推断 `<backend_service>`、`<static_service>`、`<db_service>`。
2. 读取前端 `package.json`：
   - 识别 `<frontend_dir>`（常见 `frontend`；若不存在则从 compose build context 推断）。
   - 识别 `<build_cmd>`：优先 `yarn build`，否则 `npm run build`。
3. 生成“参数草案”并向用户做**一次确认**（仅首次）：
   - 例如：`compose_cmd=docker compose, frontend_dir=frontend, static_service=nginx, backend_service=backend, db_service=db`。
4. 用户确认后，本次会话后续命令全部复用，不再重复询问。
5. 若探测冲突（多 compose 文件、多前端目录、多后端服务），只问 1 个关键问题让用户二选一。

## 何时使用

- 用户说**修改完前端/后端代码，要更新部署** → 按下方「前端更新部署」或「后端更新部署」**执行**对应命令
- 用户问如何部署、启动、停止、看日志、进数据库、排错 → 按本技能给出并视情况执行命令

**判断前端还是后端**：用户未明确说明时，优先根据**上下文**推断——对话内容（如「页面」「接口」「刚改了 xx」）、当前或最近打开/编辑的文件路径（如 frontend/、django/ 或后端目录）、用词（Vue/静态 vs API/Django）等。无法推断时再问「要更新前端、后端，还是两者？」。

不同项目的**服务名**（nginx/web/backend/db）、**前端目录**可能不同，先看当前项目的 `docker-compose.yml` 或 DEPLOY/README 再执行。

---

## 前端更新部署（可执行）

当用户表示**前端代码已改完、需要更新部署**时，先判断静态服务如何拿到构建产物：

- **A 类：dist 通过 volume 挂载进容器** → 本地构建后 `restart` 即可生效。
- **B 类：dist 在 Dockerfile 里 `COPY --from=build` 打进镜像**（compose 中该服务只有 `build:`、没有挂载 dist 的 volume）→ **必须重建镜像**，`restart` 不会更新任何文件。

判断方法：看 `docker-compose.yml` 中静态服务是否有指向前端产物目录的 `volumes`。

**A 类命令：**
```bash
cd <frontend_dir> && <build_cmd> && cd .. && <compose_cmd> restart <static_service>
```

**B 类命令（本项目 `frontend`、`admin` 均属此类）：**
```bash
<compose_cmd> up -d --build <static_service>
```

完成后可校验容器内实际产物：`<compose_cmd> exec <static_service> cat /usr/share/nginx/html/index.html`，确认引用的 JS 文件名与本次构建输出一致。

最后提示用户浏览器 Ctrl+F5 强刷。

---

## 后端更新部署（可执行）

当用户表示**后端代码已改完、需要更新部署**时，执行：`<compose_cmd> restart <backend_service>`。

**通用模板命令：**
```bash
<compose_cmd> restart <backend_service>
```

**占位示例**（将 `backend`、`docker compose` 换成当前项目探测结果）：
```bash
docker compose restart backend
```

---

## 环境要求（通用）

- Docker Desktop、Docker Compose
- 若需本地构建前端：Node.js + Yarn/npm

---

## 首次部署（通用）

1. 克隆并进入项目目录
2. 配置 .env（按项目说明）
3. `<compose_cmd> up -d --build`
4. 若有前端需先构建：见上方「前端更新部署」步骤，然后重启静态服务
5. 根据 compose 或文档确认访问端口与地址

---

## 日常操作

| 操作 | 命令 |
|------|------|
| 启动 | `<compose_cmd> up -d` |
| 停止 | `<compose_cmd> down` |
| 状态 | `<compose_cmd> ps` |
| 日志 | `<compose_cmd> logs -f` 或 `<compose_cmd> logs -f <service>` |

---

## 数据库与 exec

- 进数据库：`<compose_cmd> exec <db_service> <db_client_cmd>`（如 `mysql -u root -p`、`psql -U postgres`）
- 应用内命令：`<compose_cmd> exec <backend_service> <cmd>`（如 `python manage.py migrate`）

---

## 常见问题

- **前端不生效**：重新 build → 重启静态服务 → 浏览器 Ctrl+F5
- **清空重来**：`docker compose down -v`，再 `docker compose up -d --build`
- **资源占用**：`docker stats`
- **端口/服务名**：查项目 `docker-compose.yml` 或 DEPLOY/README

详细示例见本技能目录下的 `reference.md`。
