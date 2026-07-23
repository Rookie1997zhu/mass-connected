import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.chat.masking import mask_contact_info
from apps.chat.models import Conversation, Message

logger = logging.getLogger(__name__)

ONLINE_KEY = "chat:online:{user_id}"
UNREAD_KEY = "chat:unread:{user_id}"
CONN_KEY = "chat:conn:{user_id}"
RATE_KEY = "chat:rate:{user_id}"


def user_group_name(user_id: int) -> str:
    return f"chat.user.{user_id}"


def is_user_online(user_id: int) -> bool:
    return bool(cache.get(ONLINE_KEY.format(user_id=user_id)))


def set_user_online(user_id: int, channel_name: str | None = None):
    ttl = getattr(settings, "CHAT_ONLINE_TTL_SECONDS", 60)
    cache.set(ONLINE_KEY.format(user_id=user_id), "1", ttl)
    if channel_name:
        prev = cache.get(CONN_KEY.format(user_id=user_id))
        cache.set(CONN_KEY.format(user_id=user_id), channel_name, ttl)
        return prev
    return None


def check_rate_limit(user_id: int) -> bool:
    """True = 允许发送。按分钟桶计数。"""
    limit = getattr(settings, "CHAT_RATE_LIMIT_PER_MINUTE", 30)
    bucket = timezone.now().strftime("%Y%m%d%H%M")
    key = f"{RATE_KEY.format(user_id=user_id)}:{bucket}"
    count = cache.get(key)
    if count is None:
        cache.set(key, 1, 70)
        return True
    count = int(count)
    if count >= limit:
        return False
    cache.set(key, count + 1, 70)
    return True


def refresh_user_online(user_id: int):
    ttl = getattr(settings, "CHAT_ONLINE_TTL_SECONDS", 60)
    cache.set(ONLINE_KEY.format(user_id=user_id), "1", ttl)
    conn = cache.get(CONN_KEY.format(user_id=user_id))
    if conn:
        cache.set(CONN_KEY.format(user_id=user_id), conn, ttl)


def clear_user_online(user_id: int, channel_name: str | None = None):
    if channel_name:
        current = cache.get(CONN_KEY.format(user_id=user_id))
        if current and current != channel_name:
            return
    cache.delete(ONLINE_KEY.format(user_id=user_id))
    cache.delete(CONN_KEY.format(user_id=user_id))


def get_unread_count(user_id: int) -> int:
    return int(cache.get(UNREAD_KEY.format(user_id=user_id)) or 0)


def incr_unread(user_id: int, amount: int = 1) -> int:
    key = UNREAD_KEY.format(user_id=user_id)
    current = get_unread_count(user_id)
    total = current + amount
    cache.set(key, total, None)
    return total


def clear_conversation_unread(user_id: int, conversation: Conversation):
    conv_key = f"chat:unread_conv:{user_id}:{conversation.id}"
    pending = int(cache.get(conv_key) or 0)
    if pending:
        total = max(0, get_unread_count(user_id) - pending)
        cache.set(UNREAD_KEY.format(user_id=user_id), total, None)
        cache.delete(conv_key)
    return get_unread_count(user_id)


def incr_conversation_unread(user_id: int, conversation_id: int):
    conv_key = f"chat:unread_conv:{user_id}:{conversation_id}"
    pending = int(cache.get(conv_key) or 0)
    cache.set(conv_key, pending + 1, None)
    return incr_unread(user_id, 1)


def get_or_create_conversation_for_quote_request(quote_request):
    conversation, _created = Conversation.objects.get_or_create(
        quote_request=quote_request,
        defaults={
            "buyer": quote_request.rfq.buyer,
            "supplier": quote_request.supplier,
        },
    )
    return conversation


def link_conversation_to_order(quote_request_id, production_order=None, project=None):
    if not quote_request_id:
        return None
    try:
        conversation = Conversation.objects.get(quote_request_id=quote_request_id)
    except Conversation.DoesNotExist:
        return None
    fields = []
    if production_order and conversation.production_order_id != production_order.id:
        conversation.production_order = production_order
        fields.append("production_order")
    if project and conversation.project_id != project.id:
        conversation.project = project
        fields.append("project")
    if fields:
        fields.append("updated_at")
        conversation.save(update_fields=fields)
    return conversation


def participant_role(conversation: Conversation, user) -> str | None:
    if user is None:
        return None
    if conversation.buyer_id == user.id:
        return Message.ROLE_BUYER
    if conversation.supplier_id == user.id:
        return Message.ROLE_SUPPLIER
    return None


def user_can_access_conversation(user, conversation: Conversation, *, for_admin=False) -> bool:
    if for_admin:
        return conversation.dispute_status == Conversation.DISPUTE_OPEN and user.role in {
            "super_admin",
            "operator",
            "sales",
        }
    return participant_role(conversation, user) is not None


def push_to_user(user_id: int, event_type: str, payload: dict):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            user_group_name(user_id),
            {"type": "chat.event", "event": event_type, "payload": payload},
        )
    except Exception:  # noqa: BLE001
        logger.exception("chat push failed user_id=%s event=%s", user_id, event_type)


def serialize_message_brief(message: Message) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "sender_role": message.sender_role,
        "body": message.body,
        "has_contact_hint": message.has_contact_hint,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@transaction.atomic
def send_message(*, conversation: Conversation, sender, sender_role: str, body: str) -> Message:
    max_len = getattr(settings, "CHAT_MESSAGE_MAX_LENGTH", 4000)
    text = (body or "").strip()
    if not text:
        raise ValueError("EMPTY_BODY")
    if len(text) > max_len:
        raise ValueError("BODY_TOO_LONG")

    masked, hinted = mask_contact_info(text)
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        sender_role=sender_role,
        body=masked,
        body_original=text,
        has_contact_hint=hinted,
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return message


def after_message_sent(message: Message, *, notify_offline=True):
    conversation = message.conversation
    brief = serialize_message_brief(message)
    recipients = {conversation.buyer_id, conversation.supplier_id}
    if message.sender_id:
        recipients.discard(message.sender_id)

    for uid in recipients:
        incr_conversation_unread(uid, conversation.id)
        push_to_user(
            uid,
            "new_message",
            {**brief, "unread_total": get_unread_count(uid)},
        )
        push_to_user(
            uid,
            "unread_updated",
            {"count": get_unread_count(uid), "conversation_id": conversation.id},
        )
        if notify_offline and not is_user_online(uid):
            try:
                from apps.chat.tasks import notify_chat_message_async

                notify_chat_message_async.delay(uid, conversation.id, message.id)
            except Exception:  # noqa: BLE001
                logger.exception("enqueue chat notify failed user_id=%s", uid)

    # 发送方也推 conversation_updated，便于多端同步
    if message.sender_id:
        push_to_user(message.sender_id, "conversation_updated", brief)

    if conversation.dispute_status == Conversation.DISPUTE_OPEN:
        # 纠纷中通知在线管理员不强制；消息已落库
        pass


def open_dispute(conversation: Conversation, user, reason: str = "") -> Conversation:
    if conversation.dispute_status == Conversation.DISPUTE_OPEN:
        return conversation
    conversation.dispute_status = Conversation.DISPUTE_OPEN
    conversation.disputed_by = user
    conversation.disputed_at = timezone.now()
    conversation.dispute_reason = (reason or "")[:2000]
    conversation.save(
        update_fields=[
            "dispute_status",
            "disputed_by",
            "disputed_at",
            "dispute_reason",
            "updated_at",
        ]
    )
    payload = {
        "conversation_id": conversation.id,
        "dispute_status": conversation.dispute_status,
    }
    for uid in (conversation.buyer_id, conversation.supplier_id):
        push_to_user(uid, "dispute_updated", payload)
    try:
        from apps.chat.tasks import notify_chat_dispute_async

        notify_chat_dispute_async.delay(conversation.id)
    except Exception:  # noqa: BLE001
        logger.exception("enqueue dispute notify failed conversation_id=%s", conversation.id)
    return conversation


def resolve_dispute(conversation: Conversation) -> Conversation:
    conversation.dispute_status = Conversation.DISPUTE_RESOLVED
    conversation.save(update_fields=["dispute_status", "updated_at"])
    payload = {
        "conversation_id": conversation.id,
        "dispute_status": conversation.dispute_status,
    }
    for uid in (conversation.buyer_id, conversation.supplier_id):
        push_to_user(uid, "dispute_updated", payload)
    return conversation
