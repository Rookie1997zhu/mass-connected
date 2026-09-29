import logging

logger = logging.getLogger(__name__)

VALID_TYPES = {
    "quote",
    "project",
    "payment",
    "contract",
    "production_order",
    "quote_request",
    "point",
    "system",
    "inquiry",
    "order",
    "chat",
    "blog",
}

STAFF_ROLES = {"super_admin", "operator", "sales"}


def notify(user, ntype, title, content="", related_type="", related_id=None, send_email=False):
    """创建站内通知，可选发送邮件。失败不影响主流程。"""
    if user is None:
        return None
    from apps.notification.models import Notification

    if ntype not in VALID_TYPES:
        ntype = "system"
    notification = None
    try:
        notification = Notification.objects.create(
            user=user,
            type=ntype,
            title=title,
            content=content or "",
            related_type=related_type or "",
            related_id=related_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("create notification failed")

    if send_email and user.email:
        try:
            from apps.simplequote.heavy_tasks import send_notification_email

            send_notification_email.delay(
                f"[MASS CONNECTED] {title}",
                content or title,
                user.email,
            )
        except Exception:  # noqa: BLE001
            logger.exception("enqueue email notification failed user=%s", user.email)

    return notification


def notify_staff(ntype, title, content="", related_type="", related_id=None, send_email=False):
    """向所有活跃管理员/运营/销售角色发送站内通知。"""
    from apps.accounts.models import User

    for user in User.objects.filter(role__in=STAFF_ROLES, is_active=True):
        notify(user, ntype, title, content, related_type, related_id, send_email)
