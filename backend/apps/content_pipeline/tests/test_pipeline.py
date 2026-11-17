"""内容流水线单元测试（mock 外网）。"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.blog.models import BlogPost
from apps.content_pipeline.config import language_for_index
from apps.content_pipeline.models import PipelineItem, PipelineRun, UsedYouTubeVideo
from apps.content_pipeline.publish import assert_no_youtube_links, publish_blog_post
from apps.content_pipeline.exceptions import PipelineError
from apps.content_pipeline.rewrite import _extract_json, _strip_youtube_urls
from apps.content_pipeline.services import process_pipeline_item, run_daily_batch

User = get_user_model()


class ConfigHelpersTests(TestCase):
    def test_language_rotation_zh_ko(self):
        with override_settings(CONTENT_PIPELINE_LANGUAGES="zh,ko"):
            self.assertEqual(language_for_index(0), "zh")
            self.assertEqual(language_for_index(1), "ko")
            self.assertEqual(language_for_index(2), "zh")


class RewriteHelpersTests(TestCase):
    def test_strip_youtube_urls(self):
        text = "见 https://youtu.be/abc123 与 http://www.youtube.com/watch?v=x"
        cleaned = _strip_youtube_urls(text)
        self.assertNotIn("youtu.be", cleaned)
        self.assertNotIn("youtube.com", cleaned)

    def test_extract_json_from_fence(self):
        raw = '```json\n{"title":"T","summary":"S","content_html":"<p>x</p>","tags":[]}\n```'
        data = _extract_json(raw)
        self.assertEqual(data["title"], "T")


class PublishGuardsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="pipeline_author@test.local",
            password="pass12345",
            role="super_admin",
            is_active=True,
            is_verified=True,
        )

    def test_reject_youtube_links(self):
        with self.assertRaises(PipelineError) as ctx:
            assert_no_youtube_links("ok", "see https://youtube.com/watch?v=1")
        self.assertEqual(ctx.exception.code, "YOUTUBE_LINK_FORBIDDEN")

    @override_settings(CONTENT_PIPELINE_AUTHOR_EMAIL="pipeline_author@test.local")
    def test_publish_sets_published_at(self):
        post = publish_blog_post(
            title="测试稿",
            summary="摘要",
            content_html="<p>正文</p>",
            language="zh",
            tags=["OEM"],
            author=self.author,
        )
        self.assertEqual(post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIsNotNone(post.published_at)


@override_settings(
    CONTENT_PIPELINE_ENABLED=False,
    CONTENT_PIPELINE_DAILY_COUNT=2,
    CONTENT_PIPELINE_KEYWORDS="PCB",
    CONTENT_PIPELINE_AUTHOR_EMAIL="pipeline_author@test.local",
    CELERY_TASK_ALWAYS_EAGER=True,
)
class RunDailyBatchTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="pipeline_author@test.local",
            password="pass12345",
            role="super_admin",
            is_active=True,
            is_verified=True,
        )

    def test_disabled_creates_disabled_run_without_posts(self):
        result = run_daily_batch(sync=True)
        self.assertTrue(result.get("disabled"))
        run = PipelineRun.objects.get(pk=result["run_id"])
        self.assertEqual(run.status, PipelineRun.STATUS_DISABLED)
        self.assertEqual(BlogPost.objects.count(), 0)

    @override_settings(CONTENT_PIPELINE_ENABLED=True, YOUTUBE_API_KEY="fake-key")
    @patch("apps.content_pipeline.services.collect_candidates")
    @patch("apps.content_pipeline.services.fetch_transcript_text")
    @patch("apps.content_pipeline.services.rewrite_transcript_to_article")
    @patch("apps.content_pipeline.services.build_cover_image", return_value="")
    @patch("apps.content_pipeline.services.inject_inline_images", side_effect=lambda html, *_a, **_k: html)
    def test_sync_batch_publishes_and_dedupes(
        self,
        _inject,
        _cover,
        mock_rewrite,
        mock_transcript,
        mock_collect,
    ):
        mock_collect.return_value = [
            {"video_id": "vid001", "title": "视频一", "keyword": "PCB"},
            {"video_id": "vid002", "title": "视频二", "keyword": "PCB"},
            {"video_id": "vid001", "title": "重复", "keyword": "PCB"},
        ]
        mock_transcript.return_value = "这是足够长的字幕内容，用于通过最短长度校验。" * 3
        mock_rewrite.side_effect = [
            {
                "title": "中文稿一",
                "summary": "摘要一",
                "content_html": "<p>正文一</p>",
                "tags": ["PCB"],
                "image_slots": 0,
                "language": "zh",
            },
            {
                "title": "한글 기사",
                "summary": "요약",
                "content_html": "<p>본문</p>",
                "tags": ["PCB"],
                "image_slots": 0,
                "language": "ko",
            },
        ]

        result = run_daily_batch(sync=True)
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(BlogPost.objects.count(), 2)
        self.assertEqual(UsedYouTubeVideo.objects.count(), 2)
        langs = set(BlogPost.objects.values_list("language", flat=True))
        self.assertEqual(langs, {"zh", "ko"})

        # 再次处理同 video 应 skip
        existing = PipelineRun.objects.get(pk=result["run_id"])
        item = PipelineItem.objects.create(
            run=existing,
            youtube_video_id="vid001",
            keyword="PCB",
            language="zh",
            status=PipelineItem.STATUS_PENDING,
        )
        before = BlogPost.objects.count()
        process_pipeline_item(item.id)
        item.refresh_from_db()
        self.assertEqual(item.status, PipelineItem.STATUS_SKIPPED)
        self.assertEqual(BlogPost.objects.count(), before)

    @override_settings(CONTENT_PIPELINE_ENABLED=True, YOUTUBE_API_KEY="fake-key")
    @patch("apps.content_pipeline.services.collect_candidates")
    @patch("apps.content_pipeline.services.fetch_transcript_text")
    def test_no_transcript_skips_without_post(self, mock_transcript, mock_collect):
        from apps.content_pipeline.exceptions import PipelineSkip

        mock_collect.return_value = [{"video_id": "vidX", "title": "无字幕", "keyword": "PCB"}]
        mock_transcript.side_effect = PipelineSkip("TRANSCRIPT_UNAVAILABLE", "无字幕")

        result = run_daily_batch(sync=True)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(BlogPost.objects.count(), 0)
        item = PipelineItem.objects.get()
        self.assertEqual(item.status, PipelineItem.STATUS_SKIPPED)
