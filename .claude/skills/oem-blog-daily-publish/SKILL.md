---
name: MASSCONNECTED-blog-daily-publish
description: >
  OEM 官网博客日更固定流程：搜集 YouTube 视频、提取字幕、润色改写、配图，
  并分别用中文(zh)与韩文(ko)经 oem-blog MCP 各发布一篇。用于 Claude Code
  定时任务、日更、双语发文、博客自动发布、YouTube 转博客。
---

# OEM 博客日更（双语发布）

固定产出：**同一主题各发 1 篇中文 + 1 篇韩文**（共 2 篇），均带封面，直接上线。

## 前置检查（任一步失败则停止并报告）

1. 确认 MCP `oem-blog` 已连接且可用（`/mcp`）。
2. MCP URL 必须是 `https://www.massconnected.com/mcp/blog`（或 `https://massconnected.com/mcp/blog`）。  
   **禁止**使用 `massconnected.blog`（该域名无效）。
3. 可用工具应包含：`blog_list_categories`、`blog_list_posts`、`blog_create_post`、`blog_update_post`、`blog_publish_post`、`blog_upload_cover`。
4. 若出现 SSL / `UNEXPECTED_EOF` / 连接失败：停止发文，报告 MCP 连接问题，不要改用错误域名重试超过 1 次。

## 硬性规则

- 每篇 `publish_now=true`，直接 `published`。
- `language` 只能是 `zh` 或 `ko`；两篇各用一种，不得两篇同语种。
- 正文、摘要、标题中 **禁止** 出现 `youtube.com` / `youtu.be` 链接。
- 深度改写，禁止大段照抄字幕原文。
- 先查重：`blog_list_posts` 用标题关键词搜索；若高度重复则换选题或换角度。
- 默认主题域：OEM/ODM、PCB/SMT、包装纸盒、制造出海、供应链（可用用户当日指定主题覆盖）。
- 文风：专业、可读、面向采购/工程读者；中文用简体；韩文用自然商务韩语。

## 进度清单（必须按序勾选）

```
- [ ] 1. 选片
- [ ] 2. 字幕
- [ ] 3. 润色大纲（中韩各一）
- [ ] 4. 配图（封面；可选文内图）
- [ ] 5. 发布中文
- [ ] 6. 发布韩文
- [ ] 7. 汇报结果
```

## Step 1 — 选片

优先使用已安装的 YouTube 相关 Skill/工具（如字幕转录插件）按关键词找 **1** 个有字幕的视频。

关键词候选（轮换或由定时任务参数指定）：

- PCB 制造 / SMT 贴片
- 纸盒包装 / 刀版
- OEM 代工 / ODM
- 电子制造 / 供应链

选片要求：

- 有可用字幕（自动字幕也可）
- 内容可改写成制造/OEM 博客，而非纯娱乐
- 记下：视频标题、核心观点 3～5 条（仅作素材，不写进最终链接）

若找不到有字幕视频：换关键词再试，最多 3 个关键词；仍失败则结束并说明原因。

## Step 2 — 字幕

提取完整或足够长的字幕文本（建议 ≥ 500 字有效内容）。字幕过短则换片，回到 Step 1。

## Step 3 — 润色

基于字幕做 **两份独立成稿**（不是机翻粘贴）：

| 字段 | 要求 |
| --- | --- |
| title | ≤ 80 字，有信息量 |
| summary | 2～4 句 |
| content_markdown | 含小标题、列表；可含 1～2 处文内图占位说明 |
| tags | 3～5 个 |

先完成中文稿，再写韩文稿（同主题本地化，允许结构调整）。

## Step 4 — 配图

1. 准备封面图（优先与主题相关的实拍/产品/产线氛围图；可用浏览器或已有工具获取图片文件）。
2. 调用 `blog_upload_cover`：传入 `filename`、`content_base64`、合适的 `content_type`。
3. 记下返回的 `url`，作为两篇的 `cover_image`（中韩可共用同一封面；若有两张更贴语种的图可分别上传）。
4. 上传失败：仍可发文，但须在汇报中标明「无封面」。

文内图：若 MCP/环境不便上传多图，保证封面即可；正文用结构化小标题补偿视觉节奏。

## Step 5 — 发布中文

```
blog_create_post(
  title=...,
  summary=...,
  content_markdown=...,
  language="zh",
  tags=[...],
  cover_image=<上传返回的 url>,
  publish_now=true
)
```

成功条件：返回 `ok: true` 且有文章 `id`。失败则读报错，修复后重试最多 2 次；仍失败则停止，不要盲发韩文前假装成功。

## Step 6 — 发布韩文

同 Step 5，`language="ko"`，使用韩文标题/摘要/正文。

可选：`blog_list_categories` 后填 `category_id`（有明确分类时再填，勿乱选）。

## Step 7 — 汇报格式

```markdown
## 日更结果
- 选片：<视频主题一句话>（不放链接也可）
- 中文：id=<id>，title=<标题>，cover=<有/无>
- 韩文：id=<id>，title=<标题>，cover=<有/无>
- 异常：<无 / 具体错误>
```

## 定时任务用法

Claude Code 定时任务提示词建议直接写：

```text
执行技能 /oem-blog-daily-publish。今日关键词：<可选>。严格按 Skill 发布 zh + ko 各一篇并配封面。
```

## 故障速查

| 现象 | 处理 |
| --- | --- |
| SSL / EOF / 连不上 MCP | 检查 URL 是否为 massconnected.com；检查 API Key；停止 |
| 401 / Key 无效 | 报告需配置 Bearer Key；停止 |
| 上传封面失败 | 无封面继续发文并记录 |
| 字幕失败 | 换片，最多 3 次 |
| 标题重复 | 换角度重写后再发 |
