import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from users.models import CustomUser
from pets.models import Pet
from .models import Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.room_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data['content']
        receiver_id = data['receiver_id']
        pet_id = data['pet_id']
        
        message = await self.create_message(content, receiver_id, pet_id)
        if message:
            await self.channel_layer.group_send(
                f'user_{receiver_id}',
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'sender': {
                            'id': str(self.user.id),  # Convert UUID to string
                            'username': self.user.username,
                            'profile_picture': self.user.profile_picture.url if self.user.profile_picture else None
                        },
                        'receiver': {
                            'id': str(receiver_id),
                            'username': message.receiver.username,
                            'profile_picture': message.receiver.profile_picture.url if message.receiver.profile_picture else None
                        },
                        'pet': pet_id,
                        'content': content,
                        'timestamp': message.timestamp.isoformat(),
                        'is_read': False
                    }
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))

    @database_sync_to_async
    def create_message(self, content, receiver_id, pet_id):
        try:
            receiver = CustomUser.objects.get(id=receiver_id)
            pet = Pet.objects.get(id=pet_id)
            return Message.objects.create(
                sender=self.user,
                receiver=receiver,
                pet=pet,
                content=content
            )
        except (CustomUser.DoesNotExist, Pet.DoesNotExist):
            return None