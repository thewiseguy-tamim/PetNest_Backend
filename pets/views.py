from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from sslcommerz_lib import SSLCOMMERZ
import uuid
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Pet, PetImage, Payment
from .serializers import PetSerializer, PaymentSerializer
from .filters import PetFilter
from rest_framework.permissions import AllowAny

# Set up logging
logger = logging.getLogger(__name__)

class IsVerifiedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsAdminOrModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

class PetCreateView(generics.CreateAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    parser_classes = [MultiPartParser, FormParser]
    # permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]

    def create(self, request, *args, **kwargs):
        user = request.user

        # Map frontend key "images" -> serializer field "image" (single file)
        data = request.data.copy()
        try:
            # If "image" not provided but "images" is, take the first file
            if 'image' not in data:
                if 'images' in request.FILES:
                    files = request.FILES.getlist('images')
                    if files:
                        data['image'] = files[0]
                elif 'images' in data and 'images' in request.FILES:
                    # Fallback if data has key but actual file is in FILES
                    file_candidate = request.FILES.get('images')
                    if file_candidate:
                        data['image'] = file_candidate
        except Exception as e:
            logger.error(f"Error mapping images -> image: {e}")

        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        is_for_adoption = validated_data.get('is_for_adoption', False)

        # First post is free, otherwise payment required
        with transaction.atomic():
            if user.first_post_free:
                pet = serializer.save(owner=user)
                from users.models import Post
                Post.objects.create(
                    user=user,
                    pet=pet,
                    is_free=True,
                    is_paid=False
                )
                user.first_post_free = False
                user.save()

                pet_payload = PetSerializer(pet, context={'request': request}).data
                headers = self.get_success_headers(pet_payload)
                return Response(pet_payload, status=status.HTTP_201_CREATED, headers=headers)

            # Payment needed path
            amount = 5.00 if is_for_adoption else 20.00
            transaction_id = str(uuid.uuid4())
            pet = serializer.save(owner=user)

            sslcommerz_settings = {
                'store_id': settings.SSLCOMMERZ_STORE_ID,
                'store_pass': settings.SSLCOMMERZ_STORE_PASSWORD,
                'issandbox': settings.SSLCOMMERZ_SANDBOX
            }
            sslcommerz = SSLCOMMERZ(sslcommerz_settings)

            post_body = {
                'total_amount': amount,
                'currency': "USD",
                'tran_id': transaction_id,
                'success_url': settings.SSLCOMMERZ_SUCCESS_URL,
                'fail_url': settings.SSLCOMMERZ_FAIL_URL,
                'cancel_url': settings.SSLCOMMERZ_CANCEL_URL,
                'emi_option': 0,
                'cus_name': user.username,
                'cus_email': user.email,
                'cus_phone': user.phone or 'N/A',
                'cus_add1': user.address or 'N/A',
                'cus_add2': user.address or 'N/A',
                'cus_city': user.city or 'Dhaka',
                'cus_state': user.state or 'Dhaka',
                'cus_postcode': user.postcode or '1000',
                'cus_country': 'Bangladesh',
                'shipping_method': 'NO',
                'num_of_item': 1,
                'product_name': f"Pet {'Adoption' if is_for_adoption else 'Sale'} Post",
                'product_category': 'Pet Listing',
                'product_profile': 'general'
            }

            try:
                response = sslcommerz.createSession(post_body)
                if response.get('status') == 'SUCCESS' and response.get('GatewayPageURL'):
                    Payment.objects.create(
                        user=user,
                        pet=pet,
                        transaction_id=transaction_id,
                        amount=amount
                    )
                    return Response({
                        'payment_url': response['GatewayPageURL'],
                        'transaction_id': transaction_id,
                        'pet': PetSerializer(pet, context={'request': request}).data
                    }, status=status.HTTP_202_ACCEPTED)
                else:
                    pet.delete()
                    logger.error(f"Payment initiation failed: {response.get('failedreason', 'Unknown error')}")
                    return Response({
                        'detail': f"Payment initiation failed: {response.get('failedreason', 'Unknown error')}"
                    }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                pet.delete()
                logger.error(f"Payment initiation error: {str(e)}")
                return Response({
                    'detail': f"Payment initiation failed: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PetListView(generics.ListAPIView):
    queryset = Pet.objects.filter(availability=True)
    serializer_class = PetSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PetFilter
    permission_classes = [AllowAny]  # Allow any user to create a pet post

class PetDetailView(generics.RetrieveAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [AllowAny]

class PetUpdateView(generics.UpdateAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser, IsOwner]

class PetDeleteView(generics.DestroyAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser, IsOwner]

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.availability = False
            instance.save()

class PetImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, pk):
        try:
            pet = Pet.objects.get(pk=pk, owner=request.user)
        except Pet.DoesNotExist:
            return Response({'detail': 'Pet not found or unauthorized'}, status=404)

        images = request.FILES.getlist('images')
        if not images:
            return Response({'detail': 'No images provided'}, status=400)
        if len(images) > 5:
            return Response({'detail': 'Maximum 5 images allowed'}, status=400)

        with transaction.atomic():
            for image in images:
                PetImage.objects.create(pet=pet, image=image)

        return Response({'detail': 'Images uploaded successfully'}, status=201)

class PaymentCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        transaction_id = request.data.get('tran_id')
        status_val = request.data.get('status')
        val_id = request.data.get('val_id', '')

        sslcommerz_settings = {
            'store_id': settings.SSLCOMMERZ_STORE_ID,
            'store_pass': settings.SSLCOMMERZ_STORE_PASSWORD,
            'issandbox': settings.SSLCOMMERZ_SANDBOX
        }
        sslcommerz = SSLCOMMERZ(sslcommerz_settings)

        try:
            verification = sslcommerz.hash_validate(request.data)
            if not verification:
                logger.warning(f"Invalid payment callback for transaction {transaction_id}")
                return Response({'detail': 'Invalid payment callback'}, status=400)

            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for transaction {transaction_id}")
            return Response({'detail': 'Payment not found'}, status=404)
        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}")
            return Response({'detail': 'Payment processing failed'}, status=400)

        with transaction.atomic():
            if status_val == 'VALID':
                payment.status = Payment.Status.COMPLETED
                from users.models import Post
                Post.objects.create(
                    user=payment.user,
                    pet=payment.pet,
                    is_paid=True
                )
                # Send email confirmation
                subject = 'Payment Confirmation - PetNest'
                html_message = render_to_string('payment_confirmation_email.html', {
                    'user': payment.user,
                    'pet': payment.pet,
                    'transaction_id': payment.transaction_id,
                    'amount': payment.amount,
                    'created_at': payment.created_at
                })
                plain_message = strip_tags(html_message)
                try:
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [payment.user.email],
                        html_message=html_message
                    )
                    logger.info(f"Payment confirmation email sent to {payment.user.email}")
                except Exception as e:
                    logger.error(f"Failed to send payment confirmation email: {str(e)}")
            else:
                payment.status = Payment.Status.FAILED
                payment.pet.delete()
            payment.save()

        return Response({'detail': 'Payment processed'}, status=200)

class PaymentHistoryView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Payment.objects.all().select_related('user', 'pet')
        return Payment.objects.filter(user=user).select_related('user', 'pet')