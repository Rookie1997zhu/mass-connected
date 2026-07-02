---
name: self-check-after-change
description: 代码修改后的自检与发布前验证流程。覆盖后端健康检查、前端 lint/build、Docker 服务重启与结果分级，目标是不影响系统运行。
---

# 修改后自检（通用）

## 项目参数（先识别）

执行前先识别并替换参数位：

- `<compose_cmd>`：`docker compose` 或 `docker-compose`
- `<backend_service>`：后端服务名（如 `backend`/`api`）
- `<static_service>`：静态服务名（如 `nginx`/`web`）
- `<frontend_dir>`：前端目录（如 `frontend`）
- `<lint_cmd>`：前端 lint 命令（如 `yarn lint`）
- `<build_cmd>`：前端构建命令（如 `yarn build`）

若识别失败，先询问用户或读取项目部署文档后再执行。

### 自动探测与确认（建议默认执行）

1. 先复用 `docker-deploy` 技能的参数探测结果；若当前会话没有，则自动探测：
   - compose 命令、服务名、前端目录、lint/build 命令。
2. 生成参数草案并做一次确认：
   - `compose_cmd / backend_service / static_service / frontend_dir / lint_cmd / build_cmd`。
3. 确认后执行完整自检流程；除非用户更改环境，不重复确认。
4. 如果某项无法探测（如无前端），在结果中明确标注“无法验证/不适用”。

## 何时使用

- 用户说“帮我测试/自检一下改完有没有问题”
- 发布前希望做一轮快速回归
- 部署后需要确认服务可用性

---

## 执行原则

- 先检查、后部署；先无损检查，再做重启动作
- 默认不做破坏性操作（不清库、不重置、不删卷）
- 输出必须包含：通过项、失败项、阻塞项、建议下一步
- 若某项未被实际执行或无法取得运行证据，禁止表述为“没问题/正常”；必须明确标注为“无法验证”
- 必须形成闭环：**修改前先检查代码基线**，**部署后再复测关键项**

---

## 标准流程（可执行）

0. 修改前基线检查（防止“改前就有问题”）  
   - `<compose_cmd> exec <backend_service> python manage.py check`
   - `cd <frontend_dir> && <lint_cmd>`（至少记录 error/warning 基线）

1. 后端健康检查  
   - `<compose_cmd> exec <backend_service> python manage.py check`

2. 前端静态检查  
   - `cd <frontend_dir> && <lint_cmd>`

3. 前端构建验证  
   - `cd <frontend_dir> && <build_cmd>`

4. 服务状态检查  
   - `<compose_cmd> ps`

5. 按变更范围执行重启（必要时）  
   - 前端改动：`<compose_cmd> restart <static_service>`
   - 后端改动：`<compose_cmd> restart <backend_service>`
   - 前后端都改：两者都执行

6. 部署后复测（必须）  
   - 再次执行 `<compose_cmd> ps`
   - 至少复测 1-2 个关键路径（例如登录、核心业务页、关键 API）
   - 复测不到的项目必须标注“无法验证”

---

## 示例命令顺序（占位；服务名与目录以当前项目为准）

```bash
docker compose exec <backend_service> python manage.py check
cd <frontend_dir> && yarn lint
cd <frontend_dir> && yarn build
docker compose ps
docker compose restart <backend_service>   # 仅后端或前后端改动
docker compose restart <static_service>    # 仅前端或前后端改动
```

---

## 结果分级（统一口径）

- PASS：无 error（warnings 可记录）
- NEEDS_ATTENTION：无阻塞错误，但有较多 warning 或性能体积告警
- BLOCKED：任一关键命令失败（如 lint/build/check 失败、服务未启动）

---

## 输出模板（必须）

1. 已执行命令与结果（成功/失败）
2. 阻塞项（若有）
3. 非阻塞告警（如 bundle size）
4. 当前服务状态（列出实际服务名，如 `<backend_service>` / `<static_service>` / 数据库 / 缓存等）
5. 建议下一步（是否可部署、是否需修复）

---

## 常见失败处理

- `yarn lint` 失败：
  - 区分 error 与 warning，error 先修，warning 记录后续治理
- `yarn build` 失败：
  - 优先看首个报错文件与栈，不要先盲目清缓存
- `manage.py check` 失败：
  - 优先修 settings/import/模型注册问题
- 服务重启后异常：
  - 用 `docker compose ps` + `docker compose logs -f <service>` 定位
