"""博客文章与分类接口测试。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.blog.models import BlogCategory, BlogPost
from apps.blog.tests.client import SecureClient

User = get_user_model()

ADMIN_POSTS = "/api/admin/blog/posts"
ADMIN_CATEGORIES = "/api/admin/blog/categories"
PUBLIC_POSTS = "/api/public/blog/posts"


class BlogPostApiTests(TestCase):
    def setUp(self):
        self.client = SecureClient()
        self.admin = User.objects.create_user(
            email="blog_admin@test.local",
            password="pass12345",
            role="super_admin",
            name="编辑",
            is_active=True,
            is_verified=True,
        )
        self.member = User.objects.create_user(
            email="blog_member@test.local",
            password="pass12345",
            role="member",
            is_active=True,
            is_verified=True,
        )
        self.category = BlogCategory.objects.create(name="包装", slug="packaging", sort_order=1)

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_post(self, **overrides):
        payload = {
            "title": "纸盒结构笔记",
            "summary": "开槽箱要点",
            "content": "<p>正文</p>",
            "category": self.category.id,
            "tags": ["刀版", "纸盒"],
            "language": "zh",
            "status": "published",
        }
        payload.update(overrides)
        self._auth(self.admin)
        response = self.client.post(ADMIN_POSTS, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["data"]

    def test_member_cannot_create_post(self):
        self._auth(self.member)
        response = self.client.post(ADMIN_POSTS, {"title": "会员投稿", "status": "published"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_draft_hidden_and_pinned_first(self):
        draft = self._create_post(title="草稿", status="draft")
        pinned = self._create_post(title="置顶文章", is_pinned=True)
        self._create_post(title="普通文章", is_pinned=False)

        self.client.force_authenticate(user=None)
        listing = self.client.get(PUBLIC_POSTS)
        self.assertEqual(listing.status_code, 200)
        titles = [item["title"] for item in listing.data["data"]["items"]]
        self.assertEqual(titles[0], "置顶文章")
        self.assertNotIn("草稿", titles)
        self.assertIn("pagination", listing.data["data"])

        detail = self.client.get(f"{PUBLIC_POSTS}/{draft['id']}")
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(detail.data["code"], "BLOG_POST_NOT_FOUND")

        published = BlogPost.objects.get(pk=pinned["id"])
        self.assertIsNotNone(published.published_at)

    def test_filters_category_tag_language_keyword_and_popular(self):
        self._create_post(title="热门刀版", tags=["刀版"], language="zh")
        quiet = self._create_post(title="冷门笔记", tags=["物流"], language="en", summary="英文摘要")
        BlogPost.objects.filter(pk=quiet["id"]).update(view_count=1)
        hot = BlogPost.objects.get(title="热门刀版")
        hot.view_count = 20
        hot.save(update_fields=["view_count"])

        self.client.force_authenticate(user=None)
        by_category = self.client.get(PUBLIC_POSTS, {"category": "packaging"})
        self.assertEqual(by_category.data["data"]["pagination"]["total"], 2)

        by_tag = self.client.get(PUBLIC_POSTS, {"tag": "刀版"})
        self.assertEqual([item["title"] for item in by_tag.data["data"]["items"]], ["热门刀版"])

        by_lang = self.client.get(PUBLIC_POSTS, {"language": "en"})
        self.assertEqual([item["title"] for item in by_lang.data["data"]["items"]], ["冷门笔记"])

        by_query = self.client.get(PUBLIC_POSTS, {"q": "英文"})
        self.assertEqual([item["title"] for item in by_query.data["data"]["items"]], ["冷门笔记"])

        popular = self.client.get(PUBLIC_POSTS, {"ordering": "popular"})
        self.assertEqual(popular.data["data"]["items"][0]["title"], "热门刀版")

        featured = self.client.get(PUBLIC_POSTS, {"is_featured": "true"})
        self.assertEqual(featured.data["data"]["pagination"]["total"], 0)

    def test_category_slug_conflict(self):
        self._auth(self.admin)
        response = self.client.post(
            ADMIN_CATEGORIES,
            {"name": "重复", "slug": "packaging"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "BLOG_CATEGORY_SLUG_CONFLICT")

    def test_list_omits_content(self):
        self._create_post()
        self.client.force_authenticate(user=None)
        listing = self.client.get(PUBLIC_POSTS)
        self.assertNotIn("content", listing.data["data"]["items"][0])
