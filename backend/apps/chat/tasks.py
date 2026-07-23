from celery import shared_task

from apps.notification.services import notify, notify_staff


@shared_task(ignore_result=True)
def notify_chat_message_async(user_id: int, conversation_id: int, message_id: int):
    from apps.accounts.models import User
    from apps.chat.models import Message

    try:
        user = User.objects.get(pk=user_id)
        message = Message.objects.select_related("conversation").get(pk=message_id)
    except (User.DoesNotExist, Message.DoesNotExist):
        return
    preview = (message.body or "")[:80]
    notify(
        user,
        "chat",
        "新的聊天消息",
        preview,
        related_type="conversation",
        related_id=conversation_id,
    )


@shared_task(ignore_result=True)
def notify_chat_dispute_async(conversation_id: int):
    from apps.chat.models import Conversation

    try:
        conversation = Conversation.objects.select_related("quote_request").get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return
    qr_no = getattr(conversation.quote_request, "request_no", conversation_id)
    notify_staff(
        "chat",
        "聊天纠纷待介入",
        f"会话 #{conversation_id}（报价请求 {qr_no}）已申请平台介入。",
        related_type="conversation",
        related_id=conversation_id,
    )
