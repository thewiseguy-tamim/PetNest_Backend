from django.urls import path
from .views import (
    PetCreateView,
    PetListView,
    PetDetailView,
    PetUpdateView,
    PetDeleteView,
    PetImageUploadView,
    PaymentCallbackView,
    PaymentHistoryView,
    PetImageDeleteView
)

urlpatterns = [
    path('create/', PetCreateView.as_view(), name='pet-create'),
    path('list/', PetListView.as_view(), name='pet-list'),
    path('<int:pk>/', PetDetailView.as_view(), name='pet-detail'),
    path('<int:pk>/update/', PetUpdateView.as_view(), name='pet-update'),
    path('<int:pk>/delete/', PetDeleteView.as_view(), name='pet-delete'),
    path('<int:pk>/upload-images/', PetImageUploadView.as_view(), name='pet-upload-images'),
    path('payment/callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('payment/history/', PaymentHistoryView.as_view(), name='payment-history'),
     path('images/<int:image_id>/delete/', PetImageDeleteView.as_view(), name='pet-image-delete'),
]