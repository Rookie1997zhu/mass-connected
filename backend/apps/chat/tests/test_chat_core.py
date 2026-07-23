"""Chat unit tests: masking, rate limit keys, permission helpers."""
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.chat.masking import mask_contact_info
from apps.chat.models import Conversation
from apps.chat.services import participant_role, user_can_access_conversation
from apps.rfq.models import QuoteRequest, RFQ, ServiceCategory


User = get_user_model()


class MaskingTests(SimpleTestCase):
    def test_masks_email_phone_and_wechat(self):
        text = "联系我 wechat: abc_123 或 13812345678 / a@b.com https://evil.example"
        masked, hinted = mask_contact_info(text)
        self.assertTrue(hinted)
        self.assertNotIn("a@b.com", masked)
        self.assertNotIn("13812345678", masked)
        self.assertNotIn("https://evil.example", masked)
        self.assertIn("***", masked)

    def test_plain_text_unchanged(self):
        text = "交期 14 天，MOQ 1000"
        masked, hinted = mask_contact_info(text)
        self.assertFalse(hinted)
        self.assertEqual(masked, text)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class ConversationPermissionTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_chat@test.local", password="pass12345", role="member"
        )
        self.supplier = User.objects.create_user(
            email="supplier_chat@test.local", password="pass12345", role="factory"
        )
        self.other = User.objects.create_user(
            email="other_chat@test.local", password="pass12345", role="member"
        )
        self.admin = User.objects.create_user(
            email="admin_chat@test.local",
            password="pass12345",
            role="operator",
            is_staff=True,
        )
        self.category = ServiceCategory.objects.create(
            name={"ko": "CNC", "en": "CNC", "zh": "CNC"},
            slug="chat-test-cnc",
        )
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.category,
            quantity=100,
            status="quoted",
        )
        self.qr = QuoteRequest.objects.create(
            rfq=self.rfq, supplier=self.supplier, status="assigned"
        )
        self.conversation = Conversation.objects.create(
            quote_request=self.qr,
            buyer=self.buyer,
            supplier=self.supplier,
        )

    def test_participant_roles(self):
        self.assertEqual(participant_role(self.conversation, self.buyer), "buyer")
        self.assertEqual(participant_role(self.conversation, self.supplier), "supplier")
        self.assertIsNone(participant_role(self.conversation, self.other))

    def test_admin_requires_open_dispute(self):
        self.assertFalse(
            user_can_access_conversation(self.admin, self.conversation, for_admin=True)
        )
        self.conversation.dispute_status = Conversation.DISPUTE_OPEN
        self.conversation.save(update_fields=["dispute_status"])
        self.assertTrue(
            user_can_access_conversation(self.admin, self.conversation, for_admin=True)
        )
