from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_ticket(ticket: str):
    from apps.accounts.models import User
    from apps.chat.services import redeem_ws_ticket

    user_id = redeem_ws_ticket(ticket)
    if not user_id:
        return AnonymousUser()
    try:
        return User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """WebSocket 鉴权：仅接受一次性 ?ticket=，拒绝长期 JWT query。"""

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        ticket = (query.get("ticket") or [None])[0]
        if ticket:
            scope["user"] = await _user_from_ticket(ticket)
        else:
            scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
