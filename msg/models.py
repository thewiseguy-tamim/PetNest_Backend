from django.db import models
from django.conf import settings
from django.utils import timezone
from pets.models import Pet

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'receiver', 'pet']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"From {self.sender} to {self.receiver} about {self.pet}"