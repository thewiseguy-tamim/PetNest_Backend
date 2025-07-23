from django.urls import path
from .views import SendMessageView, ConversationListView, ConversationDetailView, MarkMessagesReadView

app_name = 'messaging'

urlpatterns = [
    path('messages/send/', SendMessageView.as_view(), name='send-message'),
    path('messages/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('messages/conversation/<uuid:user_id>/<int:pet_id>/', 
         ConversationDetailView.as_view(), 
         name='conversation-detail'),
    path('messages/mark-read/<uuid:user_id>/<int:pet_id>/', 
         MarkMessagesReadView.as_view(), 
         name='mark-messages-read'),
]