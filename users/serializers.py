from rest_framework import serializers
from .models import CustomUser, VerificationRequest, Post
from pets.models import Pet
from cloudinary.uploader import upload
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings

class VerificationRequestSerializer(serializers.ModelSerializer):
    nid_front = serializers.ImageField(use_url=True)
    nid_back = serializers.ImageField(use_url=True)

    class Meta:
        model = VerificationRequest
        fields = ['nid_number', 'nid_front', 'nid_back', 'phone', 'address', 'city', 'state', 'postcode', 'submitted_at', 'status', 'notes']
        read_only_fields = ['submitted_at', 'status', 'notes']

    def validate(self, data):
        if not data.get('nid_number'):
            raise serializers.ValidationError({"nid_number": "National ID number is required."})
        if not data.get('nid_front') or not data.get('nid_back'):
            raise serializers.ValidationError({"nid": "Both front and back images of ID are required."})
        if not data.get('phone'):
            raise serializers.ValidationError({"phone": "Phone number is required."})
        if not data.get('address'):
            raise serializers.ValidationError({"address": "Address is required."})
        if not data.get('city'):
            raise serializers.ValidationError({"city": "City is required."})
        if not data.get('state'):
            raise serializers.ValidationError({"state": "State is required."})
        if not data.get('postcode'):
            raise serializers.ValidationError({"postcode": "Postcode is required."})
        
        nid_number = data.get('nid_number')
        user = self.context['request'].user
        if CustomUser.objects.exclude(id=user.id).filter(nid_number=nid_number).exists():
            raise serializers.ValidationError({"nid_number": "This National ID number is already associated with another account."})
        
        if VerificationRequest.objects.exclude(user=user).filter(nid_number=nid_number).exists():
            raise serializers.ValidationError({"nid_number": "A verification request with this National ID number already exists."})
        
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_verified', 'verification_status', 'date_joined']
        ref_name = 'UsersUserSerializer'

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'address', 'city', 'state', 'postcode', 'profile_picture']
        read_only_fields = ['email']

    def update(self, instance, validated_data):
        profile_picture = validated_data.pop('profile_picture', None)
        if profile_picture:
            upload_result = upload(profile_picture)
            instance.profile_picture = upload_result['public_id']
        elif profile_picture == '':
            instance.profile_picture = None
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_verified', 'verification_status', 'date_joined', 'phone', 'address', 'city', 'state', 'postcode']

class PostSerializer(serializers.ModelSerializer):
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all())

    class Meta:
        model = Post
        fields = ['id', 'user', 'pet', 'is_paid', 'is_free', 'created_at']
        read_only_fields = ['user', 'is_paid', 'is_free', 'created_at']

class AdminPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'user', 'pet', 'is_paid', 'is_free', 'created_at']

class AdminVerificationRequestSerializer(serializers.ModelSerializer):
    nid_front = serializers.ImageField(use_url=True)
    nid_back = serializers.ImageField(use_url=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = VerificationRequest
        fields = ['id', 'user', 'nid_number', 'nid_front', 'nid_back', 'phone', 'address', 'city', 'state', 'postcode', 'submitted_at', 'status', 'notes']

    def get_user(self, obj):
        return {
            'id': str(obj.user.id),  
            'username': obj.user.username,
            'email': obj.user.email,
        }

class AdminUserApproveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approved', 'rejected', 'pending'])
    notes = serializers.CharField(required=False, allow_blank=True)

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Incorrect password."})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email address.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = CustomUser.objects.get(email=email)
        token = RefreshToken.for_user(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{str(token.access_token)}"
        send_mail(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_token(self, value):
        try:
            token = RefreshToken(value)
            user_id = token['user_id']
            CustomUser.objects.get(id=user_id)
            return value
        except:
            raise serializers.ValidationError("Invalid or expired token.")

    def save(self):
        token = RefreshToken(self.validated_data['token'])
        user_id = token['user_id']
        user = CustomUser.objects.get(id=user_id)
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class AdminUserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=CustomUser.Role.choices)

    def validate_role(self, value):
        if value not in [choice[0] for choice in CustomUser.Role.choices]:
            raise serializers.ValidationError("Invalid role.")
        return value