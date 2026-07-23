from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth.models import AnonymousUser

from apps.chat.services import (
    clear_user_online,
    refresh_user_online,
    set_user_online,
    user_group_name,
)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        self.user_id = user.id
        self.group = user_group_name(self.user_id)
        prev_channel = await database_sync_to_async(set_user_online)(
            self.user_id, self.channel_name
        )
        if prev_channel and prev_channel != self.channel_name:
            channel_layer = get_channel_layer()
            if channel_layer:
                await channel_layer.send(
                    prev_channel,
                    {"type": "chat.force_disconnect"},
                )
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "payload": {"user_id": self.user_id}})

    async def disconnect(self, code):
        if getattr(self, "user_id", None) and getattr(self, "group", None):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await database_sync_to_async(clear_user_online)(self.user_id, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event = content.get("event")
        if event == "ping":
            await database_sync_to_async(refresh_user_online)(self.user_id)
            await self.send_json({"event": "pong", "payload": {}})

    async def chat_event(self, event):
        await self.send_json({"event": event.get("event"), "payload": event.get("payload") or {}})

    async def chat_force_disconnect(self, event):
        await self.close(code=4000)
