from django.db import models
from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Message
from .serializers import MessageSerializer, ConversationSerializer
from .permissions import IsMessageParticipant

class SendMessageView(generics.CreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        messages = Message.objects.filter(
            models.Q(sender=user) | models.Q(receiver=user)
        ).select_related('sender', 'receiver', 'pet').order_by('-timestamp')
        
        conversations = {}
        for message in messages:
            other_user = message.receiver if message.sender == user else message.sender
            key = (other_user.id, message.pet.id)
            if key not in conversations:
                conversations[key] = {
                    'other_user': other_user,
                    'pet': message.pet,
                    'latest_message': message,
                    'unread_count': Message.objects.filter(
                        models.Q(sender=other_user, receiver=user, pet=message.pet, is_read=False)
                    ).count()
                }
        return list(conversations.values())

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class ConversationDetailView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        other_user_id = self.kwargs['user_id']
        pet_id = self.kwargs['pet_id']
        
        Message.objects.filter(
            sender__id=other_user_id,
            receiver=user,
            pet__id=pet_id,
            is_read=False
        ).update(is_read=True)
        
        return Message.objects.filter(
            models.Q(sender=user, receiver__id=other_user_id) |
            models.Q(sender__id=other_user_id, receiver=user),
            pet__id=pet_id
        ).order_by('timestamp')

class MarkMessagesReadView(generics.UpdateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsMessageParticipant]
    
    def update(self, request, *args, **kwargs):
        user = self.request.user
        other_user_id = self.kwargs['user_id']
        pet_id = self.kwargs['pet_id']
        
        Message.objects.filter(
            sender__id=other_user_id,
            receiver=user,
            pet__id=pet_id,
            is_read=False
        ).update(is_read=True)
        return Response({"status": "Messages marked as read"})