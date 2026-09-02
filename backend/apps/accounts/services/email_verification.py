import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

logger = logging.getLogger(__name__)

SIGNER = TimestampSigner(salt="accounts.email-verify")
TOKEN_MAX_AGE_SECONDS = 86400
RESEND_COOLDOWN_SECONDS = 60

EMAIL_COPY = {
    "ko": {
        "subject": "[MASS CONNECTED] 이메일 인증",
        "body": (
            "안녕하세요,\n\n"
            "MASS CONNECTED 회원가입을 완료하려면 아래 링크를 클릭하여 이메일을 인증해 주세요.\n\n"
            "{link}\n\n"
            "링크는 24시간 동안 유효합니다.\n"
            "본인이 요청하지 않았다면 이 메일을 무시하세요."
        ),
    },
    "en": {
        "subject": "[MASS CONNECTED] Verify your email",
        "body": (
            "Hello,\n\n"
            "Please verify your email to complete MASS CONNECTED registration:\n\n"
            "{link}\n\n"
            "This link expires in 24 hours.\n"
            "If you did not request this, you can ignore this email."
        ),
    },
    "zh": {
        "subject": "[MASS CONNECTED] 邮箱验证",
        "body": (
            "您好，\n\n"
            "请点击以下链接完成 MASS CONNECTED 注册邮箱验证：\n\n"
            "{link}\n\n"
            "链接 24 小时内有效。\n"
            "如非本人操作，请忽略此邮件。"
        ),
    },
    "ja": {
        "subject": "[MASS CONNECTED] メール認証",
        "body": (
            "こんにちは。\n\n"
            "MASS CONNECTED の登録を完了するには、以下のリンクからメール認証を行ってください。\n\n"
            "{link}\n\n"
            "リンクの有効期限は24時間です。\n"
            "心当たりがない場合は、このメールを無視してください。"
        ),
    },
}


def normalize_lang(lang):
    code = (lang or settings.DEFAULT_LANGUAGE or "ko").split(",")[0].strip()
    code = code.split("-")[0].strip()[:2] or "ko"
    return code if code in EMAIL_COPY else "ko"


def email_fingerprint(email):
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def build_verification_token(user):
    payload = f"{user.pk}:{email_fingerprint(user.email)}"
    return SIGNER.sign(payload)


def build_verification_link(user):
    token = build_verification_token(user)
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/verify-email?token={token}"


def get_email_content(user, lang="ko"):
    lang_code = normalize_lang(lang)
    copy = EMAIL_COPY[lang_code]
    link = build_verification_link(user)
    return copy["subject"], copy["body"].format(link=link)


def confirm_verification_token(token):
    try:
        payload = SIGNER.unsign(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"

    parts = payload.split(":", 1)
    if len(parts) != 2:
        return None, "invalid"

    user_id_str, fingerprint = parts
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None, "invalid"

    from apps.accounts.models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None, "invalid"

    if email_fingerprint(user.email) != fingerprint:
        return None, "invalid"

    if user.is_verified:
        return user, "already_verified"

    user.is_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["is_verified", "email_verified_at", "updated_at"])
    return user, "verified"


def can_resend_verification(user_id):
    key = f"email_verify_resend:{user_id}"
    if cache.get(key):
        return False
    cache.set(key, 1, RESEND_COOLDOWN_SECONDS)
    return True


def enqueue_verification_email(user, lang="ko"):
    try:
        from apps.simplequote.heavy_tasks import send_verification_email

        send_verification_email.delay(user.id, lang=normalize_lang(lang))
    except Exception:  # noqa: BLE001
        logger.exception("enqueue verification email failed user_id=%s", user.id)
