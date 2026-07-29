"""聊天消息翻译异步化：缓存命中同步、未命中入队返回 job_id、任务所有者校验。"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message
from apps.rfq.models import QuoteRequest, RFQ, ServiceCategory
from core.async_jobs import create_job

User = get_user_model()

LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


@override_settings(
    CACHES=LOCMEM_CACHES,
    CELERY_TASK_ALWAYS_EAGER=True,
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class ChatTranslateAsyncTests(TestCase):
    def setUp(self):
        cache.clear()
        self.buyer = User.objects.create_user(
            email="buyer_tr@test.local", password="pass12345", role="member", is_active=True
        )
        self.supplier = User.objects.create_user(
            email="supplier_tr@test.local", password="pass12345", role="factory", is_active=True
        )
        self.other_member = User.objects.create_user(
            email="other_tr@test.local", password="pass12345", role="member", is_active=True
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC", "zh": "CNC"}, slug="chat-tr-cnc"
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer, service_category=self.category, quantity=100, status="quoted"
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="assigned"
        )
        self.conversation = Conversation.objects.create(
            quote_request=self.qr, buyer=self.buyer, supplier=self.supplier
        )
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.supplier,
            sender_role=Message.ROLE_SUPPLIER,
            body="交期需要多久？",
        )
        self.buyer_client = APIClient()
        self.buyer_client.force_authenticate(user=self.buyer)

    def _translate_url(self):
        return (
            f"/api/member/chat/conversations/{self.conversation.id}"
            f"/messages/{self.message.id}/translate"
        )

    def test_cache_hit_returns_sync(self):
        cache.set(f"chat:msg_tr:{self.message.id}:en", "How long is the lead time?", 3600)
        res = self.buyer_client.post(
            self._translate_url(), {"target_lang": "en"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["code"], "OK")
        self.assertEqual(res.data["data"]["translated_text"], "How long is the lead time?")
        self.assertEqual(res.data["data"]["status"], "done")

    @patch("apps.project.translation.translate_text", return_value="How long is the lead time?")
    def test_cache_miss_enqueues_job_and_poll_done(self, mock_translate):
        res = self.buyer_client.post(
            self._translate_url(), {"target_lang": "en"}, format="json"
        )
        self.assertEqual(res.status_code, 202, res.data)
        job_id = res.data["data"]["job_id"]
        self.assertTrue(job_id)
        self.assertEqual(res.data["data"]["status"], "pending")
        mock_translate.assert_called_once()

        # 任务在 eager 模式下已执行完毕并写入缓存
        self.assertEqual(
            cache.get(f"chat:msg_tr:{self.message.id}:en"), "How long is the lead time?"
        )

        poll_res = self.buyer_client.get(f"/api/member/chat/translate-jobs/{job_id}")
        self.assertEqual(poll_res.status_code, 200, poll_res.data)
        self.assertEqual(poll_res.data["data"]["status"], "done")
        self.assertEqual(
            poll_res.data["data"]["result"]["translated_text"], "How long is the lead time?"
        )

    def test_non_owner_cannot_read_job(self):
        job_id = create_job(
            "chat_msg_translate", self.buyer.id, meta={"message_id": self.message.id}
        )
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_member)
        res = other_client.get(f"/api/member/chat/translate-jobs/{job_id}")
        self.assertEqual(res.status_code, 403, res.data)
        self.assertEqual(res.data["code"], "TRANSLATE_JOB_FORBIDDEN")
