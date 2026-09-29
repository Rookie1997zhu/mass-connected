"""博客点赞、评论与浏览量测试。"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from apps.blog.models import BlogPost
from apps.blog.tests.client import SecureClient

User = get_user_model()

LOCMEM = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "blog-tests"}
}


@override_settings(CACHES=LOCMEM)
class BlogInteractionApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = SecureClient()
        self.admin = User.objects.create_user(
            email="blog_editor@test.local",
            password="pass12345",
            role="operator",
            name="运营",
            is_active=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            email="blog_reader@test.local",
            password="pass12345",
            role="member",
            name="读者",
            is_active=True,
            is_verified=True,
        )
        self.other = User.objects.create_user(
            email="blog_other@test.local",
            password="pass12345",
            role="member",
            name="其他人",
            is_active=True,
            is_verified=True,
        )
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(
            "/api/admin/blog/posts",
            {"title": "可互动文章", "content": "<p>hi</p>", "status": "published", "language": "zh"},
            format="json",
        )
        self.post_id = created.data["data"]["id"]
        self.like_url = f"/api/blog/posts/{self.post_id}/like"
        self.comment_url = f"/api/blog/posts/{self.post_id}/comments"
        self.public_url = f"/api/public/blog/posts/{self.post_id}"

    def test_like_is_idempotent(self):
        self.client.force_authenticate(user=None)
        anonymous = self.client.put(self.like_url)
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_authenticate(user=self.member)
        first = self.client.put(self.like_url)
        second = self.client.put(self.like_url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.data["data"]["like_count"], 1)
        removed = self.client.delete(self.like_url)
        self.assertEqual(removed.data["data"]["like_count"], 0)
        again = self.client.delete(self.like_url)
        self.assertEqual(again.data["data"]["like_count"], 0)

    def test_comment_reply_and_delete_permission(self):
        self.client.force_authenticate(user=self.member)
        created = self.client.post(self.comment_url, {"content": "写得很清楚"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        comment_id = created.data["data"]["id"]
        reply = self.client.post(
            self.comment_url,
            {"content": "补充一句", "parent": comment_id},
            format="json",
        )
        self.assertEqual(reply.status_code, 201, reply.data)

        post = BlogPost.objects.get(pk=self.post_id)
        self.assertEqual(post.comment_count, 2)

        self.client.force_authenticate(user=self.other)
        forbidden = self.client.delete(f"/api/blog/comments/{comment_id}")
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.data["code"], "BLOG_COMMENT_FORBIDDEN")

        self.client.force_authenticate(user=self.member)
        deleted = self.client.delete(f"/api/blog/comments/{comment_id}")
        self.assertEqual(deleted.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.comment_count, 0)

    def test_hidden_comment_not_public_and_too_long(self):
        self.client.force_authenticate(user=self.member)
        created = self.client.post(self.comment_url, {"content": "需要隐藏"}, format="json")
        comment_id = created.data["data"]["id"]

        self.client.force_authenticate(user=self.admin)
        hidden = self.client.patch(
            f"/api/admin/blog/comments/{comment_id}",
            {"is_hidden": True},
            format="json",
        )
        self.assertEqual(hidden.status_code, 200)

        self.client.force_authenticate(user=None)
        listing = self.client.get(f"/api/public/blog/posts/{self.post_id}/comments")
        self.assertEqual(listing.data["data"]["items"], [])
        self.assertEqual(BlogPost.objects.get(pk=self.post_id).comment_count, 0)

        self.client.force_authenticate(user=self.member)
        too_long = self.client.post(self.comment_url, {"content": "字" * 1001}, format="json")
        self.assertEqual(too_long.status_code, 400)
        self.assertEqual(too_long.data["code"], "BLOG_COMMENT_TOO_LONG")

    def test_view_count_deduped_for_thirty_minutes(self):
        self.client.force_authenticate(user=self.member)
        first = self.client.get(self.public_url)
        second = self.client.get(self.public_url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["data"]["view_count"], 1)
        self.assertEqual(second.data["data"]["view_count"], 1)
        self.assertTrue(first.data["data"]["liked_by_me"] is False)
