"""
HotServe — Chat WebSocket Consumer

Handles real-time messaging using Django Channels.
One consumer per chat room connection.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Reject unauthenticated connections
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verify user belongs to this room
        room = await self.get_room()
        if not room:
            await self.close()
            return

        if not await self.user_in_room(room):
            await self.close()
            return

        # Check room is still active
        if not room.is_active:
            await self.send(text_data=json.dumps({
                'type': 'room_closed',
                'message': 'This chat has been closed.'
            }))
            await self.close()
            return

        self.room = room

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send connection confirmation + time remaining
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'room_id': str(room.id),
            'time_remaining': room.time_remaining_seconds,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming message from WebSocket client."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if not content or len(content) > 1000:
                return

            # Check room is still active before saving
            room = await self.get_room()
            if not room or not room.is_active:
                await self.send(text_data=json.dumps({
                    'type': 'room_closed',
                    'message': 'Chat window has closed.'
                }))
                return

            # Save message to DB
            message = await self.save_message(content)

            # Broadcast to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(message.id),
                    'content': content,
                    'sender_id': str(self.user.id),
                    'sender_name': self.user.display_name,
                    'timestamp': message.created_at.isoformat(),
                }
            )

        elif msg_type == 'toggle_photo':
            # Requester toggles profile photo visibility
            if self.user == self.room.requester:
                visible = await self.toggle_photo_visibility()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'photo_toggle',
                        'visible': visible,
                    }
                )

        elif msg_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def chat_message(self, event):
        """Receive message from room group and send to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'is_own': event['sender_id'] == str(self.user.id),
        }))

    async def photo_toggle(self, event):
        await self.send(text_data=json.dumps({
            'type': 'photo_toggle',
            'visible': event['visible'],
        }))

    async def room_closed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_closed',
            'message': event.get('message', 'Chat has been closed.'),
        }))

    # ── DB helpers ──────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_room(self):
        try:
            return ChatRoom.objects.select_related(
                'requester', 'runner', 'task'
            ).get(id=self.room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def user_in_room(self, room):
        return self.user in [room.requester, room.runner]

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            room=self.room,
            sender=self.user,
            content=content,
            message_type=Message.MessageType.TEXT,
        )

    @database_sync_to_async
    def toggle_photo_visibility(self):
        room = ChatRoom.objects.get(id=self.room_id)
        room.requester_photo_visible = not room.requester_photo_visible
        room.save(update_fields=['requester_photo_visible'])
        return room.requester_photo_visible
