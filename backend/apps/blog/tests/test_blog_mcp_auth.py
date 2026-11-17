"""博客 MCP 机器 API Key 认证测试。"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.blog.models import BlogPost
from apps.blog.tests.client import SecureClient

User = get_user_model()

ADMIN_POSTS = "/api/admin/blog/posts"
MCP_KEY = "test-blog-mcp-key-32chars-xxxxxx"
AUTHOR_EMAIL = "blog_mcp_author@test.local"


@override_settings(
    BLOG_MCP_API_KEY=MCP_KEY,
    BLOG_MCP_AUTHOR_EMAIL=AUTHOR_EMAIL,
)
class BlogMcpApiKeyAuthTests(TestCase):
    def setUp(self):
        self.client = SecureClient()
        self.author = User.objects.create_user(
            email=AUTHOR_EMAIL,
            password="pass12345",
            role="super_admin",
            name="MCP作者",
            is_active=True,
            is_verified=True,
        )

    def test_bearer_key_creates_published_post(self):
        response = self.client.post(
            ADMIN_POSTS,
            {
                "title": "MCP 直发",
                "summary": "摘要",
                "content": "<p>正文</p>",
                "language": "zh",
                "status": "published",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {MCP_KEY}",
        )
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data["data"]
        self.assertEqual(data["status"], "published")
        self.assertEqual(data["author"], self.author.id)
        post = BlogPost.objects.get(pk=data["id"])
        self.assertIsNotNone(post.published_at)

    def test_x_api_key_creates_draft(self):
        response = self.client.post(
            ADMIN_POSTS,
            {
                "title": "MCP 草稿",
                "content": "<p>草稿</p>",
                "language": "zh",
                "status": "draft",
            },
            format="json",
            HTTP_X_API_KEY=MCP_KEY,
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"]["status"], "draft")
        post = BlogPost.objects.get(pk=response.data["data"]["id"])
        self.assertIsNone(post.published_at)

    def test_invalid_x_api_key_rejected(self):
        response = self.client.post(
            ADMIN_POSTS,
            {"title": "拒绝", "status": "published"},
            format="json",
            HTTP_X_API_KEY="wrong-key",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "BLOG_MCP_KEY_INVALID")
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_invalid_author_email_rejected(self):
        with override_settings(
            BLOG_MCP_API_KEY=MCP_KEY,
            BLOG_MCP_AUTHOR_EMAIL="missing@test.local",
        ):
            response = self.client.post(
                ADMIN_POSTS,
                {"title": "无作者", "status": "draft"},
                format="json",
                HTTP_AUTHORIZATION=f"Bearer {MCP_KEY}",
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "BLOG_MCP_AUTHOR_INVALID")
        self.assertEqual(BlogPost.objects.count(), 0)
