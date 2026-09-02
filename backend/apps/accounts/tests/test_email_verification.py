from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services.email_verification import (
    build_verification_token,
    confirm_verification_token,
    email_fingerprint,
)


class EmailVerificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="verify-test@example.com",
            password="password12345",
            role="member",
            member_type="individual",
            is_verified=False,
        )

    def test_confirm_valid_token_marks_user_verified(self):
        token = build_verification_token(self.user)
        user, result = confirm_verification_token(token)
        self.assertEqual(result, "verified")
        self.assertTrue(user.is_verified)
        self.assertIsNotNone(user.email_verified_at)

    def test_confirm_token_is_idempotent_when_already_verified(self):
        self.user.is_verified = True
        self.user.email_verified_at = timezone.now()
        self.user.save(update_fields=["is_verified", "email_verified_at", "updated_at"])
        token = build_verification_token(self.user)
        user, result = confirm_verification_token(token)
        self.assertEqual(result, "already_verified")
        self.assertTrue(user.is_verified)

    def test_confirm_rejects_tampered_email(self):
        token = build_verification_token(self.user)
        self.user.email = "other@example.com"
        self.user.save(update_fields=["email", "updated_at"])
        user, result = confirm_verification_token(token)
        self.assertIsNone(user)
        self.assertEqual(result, "invalid")

    def test_email_fingerprint_is_stable(self):
        self.assertEqual(
            email_fingerprint("Test@Example.com"),
            email_fingerprint("test@example.com"),
        )

    @override_settings(FRONTEND_BASE_URL="https://www.example.com")
    def test_build_token_contains_user_id(self):
        token = build_verification_token(self.user)
        self.assertIn(":", token)
