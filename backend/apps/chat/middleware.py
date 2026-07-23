from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _user_from_token(token: str):
    from apps.accounts.models import User

    try:
        access = AccessToken(token)
        user_id = access.get("user_id")
        return User.objects.get(pk=user_id, is_active=True)
    except Exception:  # noqa: BLE001
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """WebSocket JWT：仅接受短期 access token（query ?token=）。"""

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token:
            scope["user"] = await _user_from_token(token)
        else:
            scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
