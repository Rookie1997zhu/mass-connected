# OEM Blog MCP（远程 HTTP）

给 Claude Code 连接的博客自动发布 MCP。对外路径：`/mcp/blog`。

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `BLOG_MCP_API_KEY` | 入站鉴权，并作为调用 Django 的 Bearer |
| `OEM_API_BASE_URL` | Django API 根，容器内默认 `http://backend:8000/api` |
| `BLOG_MCP_AUTHOR_EMAIL` | 配在 **Django/.env**，文章作者账号邮箱 |

Django 侧还需配置同名 `BLOG_MCP_API_KEY` 与 `BLOG_MCP_AUTHOR_EMAIL`（管理员角色用户）。

## Claude Code 连接

```bash
claude mcp add --transport http oem-blog https://你的域名/mcp/blog \
  --header "Authorization: Bearer <BLOG_MCP_API_KEY>"
```

JSON（`type` 也可用 `streamable-http`）：

```json
{
  "mcpServers": {
    "oem-blog": {
      "type": "http",
      "url": "https://你的域名/mcp/blog",
      "headers": {
        "Authorization": "Bearer <BLOG_MCP_API_KEY>"
      }
    }
  }
}
```

## Tools

- `blog_list_categories`
- `blog_list_posts`
- `blog_create_post`（`publish_now=true` 直接上线）
- `blog_update_post`
- `blog_publish_post`
- `blog_upload_cover`（Base64 → 媒体 URL）
