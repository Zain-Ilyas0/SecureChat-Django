import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Message, Profile



class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.me = self.scope['user']

        if not self.me.is_authenticated:
            await self.close()
            return

        self.other_id = int(self.scope['url_route']['kwargs']['user_id'])

        ids = sorted([self.me.id, self.other_id])
        self.room = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'room'):
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data.get('text', '').strip()

        if not text:
            return

        time = await self.save_message(text)

        await self.channel_layer.group_send(self.room, {
            'type': 'chat_message',
            'text': text,
            'time': time,
            'sender_id': self.me.id,
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'text': event['text'],
            'time': event['time'],
            'sender_id': event['sender_id'],
        }))

    @database_sync_to_async
    def save_message(self, text):
        receiver = User.objects.get(id=self.other_id)
        msg = Message.objects.create(sender=self.me, receiver=receiver, text=text)
        return timezone.localtime(msg.created_at).strftime('%I:%M %p').lstrip('0')







# user_id -> number of open tabs. A person is online while this is above 0.
online_users = {}


class PresenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.joined = False
        self.me = self.scope['user']

        if not self.me.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add("presence", self.channel_name)
        await self.accept()
        self.joined = True

        online_users[self.me.id] = online_users.get(self.me.id, 0) + 1

        # First tab opened: tell everyone this person is online
        if online_users[self.me.id] == 1:
            await self.channel_layer.group_send("presence", {
                'type': 'presence_update',
                'user_id': self.me.id,
                'online': True,
                'last_seen': '',
            })

    async def disconnect(self, code):
        if not self.joined:
            return

        await self.channel_layer.group_discard("presence", self.channel_name)

        count = online_users.get(self.me.id, 1) - 1

        if count > 0:
            # Still has another tab open
            online_users[self.me.id] = count
            return

        # Last tab closed: save last seen and tell everyone
        online_users.pop(self.me.id, None)
        last_seen = await self.save_last_seen()

        await self.channel_layer.group_send("presence", {
            'type': 'presence_update',
            'user_id': self.me.id,
            'online': False,
            'last_seen': last_seen,
        })

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            'user_id': event['user_id'],
            'online': event['online'],
            'last_seen': event['last_seen'],
        }))

    @database_sync_to_async
    def save_last_seen(self):
        now = timezone.now()
        Profile.objects.filter(user=self.me).update(last_seen=now)
        return timezone.localtime(now).strftime('%d %b, %I:%M %p')