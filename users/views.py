from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, BasePermission
from rest_framework import status, generics
from .models import CustomUser, Post, VerificationRequest
from .serializers import (
    UserSerializer, UserRegisterSerializer, UserProfileSerializer, PostSerializer,
    AdminUserSerializer, AdminPostSerializer, VerificationRequestSerializer,
    AdminVerificationRequestSerializer, AdminUserApproveSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AdminUserRoleUpdateSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class IsVerifiedUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_verified or request.user.role == CustomUser.Role.MODERATOR)

class JWTAuthenticationWithJWTScheme(JWTAuthentication):
    def get_header(self, request):
        auth_header = super().get_header(request)
        if auth_header:
            if auth_header.startswith(b'Bearer ') or auth_header.startswith(b'JWT '):
                return auth_header
        return None

    def get_raw_token(self, header):
        parts = header.decode().split()
        if parts[0] not in ('Bearer', 'JWT'):
            raise AuthenticationFailed('Invalid token header. Expected "Bearer <token>" or "JWT <token>".')
        if len(parts) != 2:
            raise AuthenticationFailed('Invalid token header. Token string should contain 1 space.')
        return parts[1]

class ModeratorOrAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [CustomUser.Role.MODERATOR, CustomUser.Role.ADMIN]

class UserRegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

class UserLoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_object(self):
        return self.request.user

class VerificationRequestView(generics.CreateAPIView):
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def perform_create(self, serializer):
        user = self.request.user
        nid_number = serializer.validated_data['nid_number']
        
        if CustomUser.objects.exclude(id=user.id).filter(nid_number=nid_number).exists() or \
           VerificationRequest.objects.exclude(user=user).filter(nid_number=nid_number).exists():
            serializer.save(
                user=user,
                status=VerificationRequest.Status.REJECTED,
                notes="Verification rejected: National ID number already in use."
            )
            user.verification_status = CustomUser.VerificationStatus.REJECTED
            user.is_verified = False
        else:
            serializer.save(user=user, status=VerificationRequest.Status.PENDING)
            user.verification_status = CustomUser.VerificationStatus.PENDING
            user.is_verified = False
        
        user.phone = serializer.validated_data['phone']
        user.address = serializer.validated_data['address']
        user.city = serializer.validated_data['city']
        user.state = serializer.validated_data['state']
        user.postcode = serializer.validated_data['postcode']
        user.nid_number = serializer.validated_data['nid_number']
        user.nid_front = serializer.validated_data['nid_front']
        user.nid_back = serializer.validated_data['nid_back']
        user.save()

class UserStatusView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get(self, request):
        return Response({
            'is_verified': request.user.is_verified,
            'role': request.user.role,
            'verification_status': request.user.verification_status,  
            'profile_picture': request.user.profile_picture.url if request.user.profile_picture else None
        })

class UserPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != CustomUser.Role.MODERATOR and not user.is_verified:
            raise serializers.ValidationError("Only verified users or moderators can create posts.")
        
        has_free_post = Post.objects.filter(user=user, is_free=True).exists()
        
        if user.role == CustomUser.Role.MODERATOR or (not has_free_post and user.first_post_free):
            serializer.save(user=user, is_free=True)
            if user.role != CustomUser.Role.MODERATOR:
                user.first_post_free = False
                user.save()
        else:
            raise serializers.ValidationError("Paid posts should be created via the pet creation endpoint.")

class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        status = self.request.query_params.get('status')
        role = self.request.query_params.get('role')
        if status:
            if status == 'verified':
                queryset = queryset.filter(is_verified=True)
            elif status == 'pending':
                queryset = queryset.filter(is_verified=False, verification_status=CustomUser.VerificationStatus.PENDING)
            elif status == 'rejected':
                queryset = queryset.filter(is_verified=False, verification_status=CustomUser.VerificationStatus.REJECTED)
        if role:
            queryset = queryset.filter(role=role)
        return queryset

class AdminUserDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]
    queryset = CustomUser.objects.all()

class AdminUserApproveView(APIView):
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]
    serializer_class = AdminUserApproveSerializer

    def post(self, request, pk):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        status_val = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        try:
            with transaction.atomic():
                try:
                    user = CustomUser.objects.get(id=pk)
                except CustomUser.DoesNotExist:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

                verification_request = VerificationRequest.objects.filter(
                    user=user,
                    status=VerificationRequest.Status.PENDING
                ).first()

                if status_val == 'approved':
                    user.is_verified = True
                    user.verification_status = CustomUser.VerificationStatus.VERIFIED
                    if verification_request:
                        verification_request.status = VerificationRequest.Status.APPROVED
                        verification_request.notes = notes
                        verification_request.save()
                elif status_val == 'rejected':
                    user.is_verified = False
                    user.verification_status = CustomUser.VerificationStatus.REJECTED
                    if verification_request:
                        verification_request.status = VerificationRequest.Status.REJECTED
                        verification_request.notes = notes
                        verification_request.save()
                elif status_val == 'pending':
                    user.is_verified = False
                    user.verification_status = CustomUser.VerificationStatus.PENDING
                    if verification_request:
                        verification_request.status = VerificationRequest.Status.PENDING
                        verification_request.notes = notes
                        verification_request.save()
                
                user.save()
                
                return Response({
                    "message": f"User verification status updated to {status_val}",
                    "user_id": user.id,
                    "status": status_val
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": f"Failed to update user status: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminUserRoleUpdateView(APIView):
    permission_classes = [IsAdminUser]
    authentication_classes = [JWTAuthenticationWithJWTScheme]
    serializer_class = AdminUserRoleUpdateSerializer

    def post(self, request, pk):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.validated_data['role']

        try:
            user = CustomUser.objects.get(id=pk)
            user.role = role
            user.is_staff = (role == CustomUser.Role.ADMIN)
            user.save()
            return Response({
                "message": f"User role updated to {role}",
                "user_id": user.id,
                "role": role
            }, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class AdminVerificationRequestListView(generics.ListAPIView):
    serializer_class = AdminVerificationRequestSerializer
    permission_classes = [ModeratorOrAdminPermission]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_queryset(self):
        queryset = VerificationRequest.objects.all()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

class AdminPostListView(generics.ListAPIView):
    serializer_class = AdminPostSerializer
    permission_classes = [ModeratorOrAdminPermission]
    authentication_classes = [JWTAuthenticationWithJWTScheme]

    def get_queryset(self):
        queryset = Post.objects.all()
        pet_type = self.request.query_params.get('pet_type')
        if pet_type:
            queryset = queryset.filter(pet__pet_type=pet_type)
        return queryset

class AdminPostDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = AdminPostSerializer
    permission_classes = [ModeratorOrAdminPermission]
    authentication_classes = [JWTAuthenticationWithJWTScheme]
    queryset = Post.objects.all()

class PasswordChangeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthenticationWithJWTScheme]
    serializer_class = PasswordChangeSerializer

    def get(self, request):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            RefreshToken.for_user(user).blacklist()
            return Response({"message": "Password changed successfully. Please log in again."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication, JWTAuthenticationWithJWTScheme]
    serializer_class = PasswordResetRequestSerializer

    def get(self, request):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset link sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def get(self, request):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            RefreshToken.for_user(user).blacklist()
            return Response({"message": "Password reset successfully. Please log in with your new password."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)