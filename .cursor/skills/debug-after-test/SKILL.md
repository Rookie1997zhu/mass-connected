---
name: debug-after-test
description: 用户开发后经测试出现问题并让你处理时，主动寻找原因。需要查看后台或服务日志时，在 Agent 模式下自动执行查看日志等命令；在 Ask 模式下给出需执行的命令并建议切换 Agent 或贴出结果。研判后给出明确结论与修复建议。
---

# 测试问题排查（开发后）

## 项目参数（先识别）

执行日志与状态命令前，先识别以下参数：

- `<compose_cmd>`：`docker compose` 或 `docker-compose`
- `<backend_service>`：后端服务名
- `<static_service>`：静态/Nginx 服务名

若项目非 Docker，再识别对应进程管理方式（systemd/pm2/本地进程）。

### 自动探测与一次确认

1. 自动探测参数：
   - `<compose_cmd>`、`<backend_service>`、`<static_service>`（来自 compose 文件）。
2. 自动生成日志命令草案并让用户一次确认（首次）：
   - `logs --tail=200 <backend_service>`
   - `logs --tail=200 <static_service>`
   - `ps`
3. 确认后复用参数，持续排查不重复询问。
4. 如果非 Docker 项目，自动切换到 `journalctl/pm2/本地日志路径` 方案并说明依据。

## 何时使用

用户表示开发完成、测试中或测试后出现问题，并让你「处理」「查一下」「看下日志」「帮忙排查」时，按本技能执行。

## 行为要求

1. **主动寻找原因**：不限于用户描述，主动从代码路径、配置、依赖、运行环境、日志等多方面排查。
2. **需要日志时**：
   - **Agent 模式**：自动执行相关命令（如 `<compose_cmd> logs -f <backend_service>`、`<compose_cmd> logs -f <static_service>`，或当前项目的日志命令），根据输出研判。
   - **Ask 模式**：无法执行命令时，给出需执行的命令原文，并说明「请在本机终端执行上述命令，或将输出贴回；也可切换到 Agent 模式由我执行」。
3. **研判后给出结论**：结合日志、代码、配置分析，给出可能原因（可多条按可能性排序），并给出具体修复建议或下一步操作。

## 建议排查顺序

1. 理解现象：复现步骤、报错信息、界面/接口表现。
2. 代码与配置：根据现象定位相关代码、配置、环境变量；查看近期改动。
3. 运行时与日志：查看后端/前端构建/nginx 等服务的日志（compose 项目常用 `docker compose logs --tail=200 <服务名>` 或 `logs -f`）。
4. 综合结论：归纳原因并给出修改建议或命令。

## DRF 接口排障必查（新增）

当报错接口是 DRF View/ViewSet（尤其是新加 action）时，必须执行以下检查：

1. **导入检查（强制）**
   - 若代码中使用 `Response(...)`，确认同文件存在：
     - `from rest_framework.response import Response`
   - 若代码中使用 `status.HTTP_*`，确认同文件存在：
     - `from rest_framework import status`
   - 不要假设 `from xxx import *` 会带入以上符号。

2. **同类符号全文件扫描**
   - 修复一个 `NameError` 后，继续扫描同文件同类符号（如 `Response`、`status`、`HTTP_`）；
   - 确认不会出现“修完一个又报下一个”的二次故障。

3. **接口级冒烟（强制）**
   - 新增/修改接口至少验证两种请求：
     - 未登录请求（预期 401/403）
     - 已登录请求（预期 2xx 或明确业务态）
   - `manage.py check` 通过不代表接口运行路径一定正确，不能替代接口级验证。

4. **日志闭环**
   - 修复并重启后，立即检查最新应用服务（如 `<backend_service>`）日志；
   - 结论必须基于“无新 traceback + 接口状态码符合预期”。

## 注意

- 服务名、日志路径以当前项目为准（如 docker-compose.yml、DEPLOY 文档）。
- 若需执行多条命令，在 Agent 模式下依次执行；在 Ask 模式下逐条列出并说明用途。
- 常用日志与状态命令见本技能目录下的 `reference.md`。
