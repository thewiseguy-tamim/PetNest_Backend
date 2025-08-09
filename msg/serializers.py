from rest_framework import serializers
from users.models import CustomUser
from pets.models import Pet
from .models import Message


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'profile_picture']


class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ['id', 'name', 'pet_type', 'breed', 'images']
        # Avoid OpenAPI name collisions if there are other Pet serializers
        ref_name = 'MsgPetSerializer'


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = serializers.SlugRelatedField(
        slug_field='username',
        queryset=CustomUser.objects.all(),
        write_only=True
    )
    receiver_detail = UserSerializer(source='receiver', read_only=True)
    pet = serializers.PrimaryKeyRelatedField(queryset=Pet.objects.all())
    # IMPORTANT: Use the same 'pet' object to build a detailed representation
    pet_detail = PetSerializer(source='pet', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'receiver',          # write-only, excluded from output
            'receiver_detail',   # read-only, shown in output
            'pet',
            'pet_detail',
            'content',
            'timestamp',
            'is_read'
        ]
        read_only_fields = ['sender', 'receiver_detail', 'timestamp', 'is_read']


class ConversationSerializer(serializers.Serializer):
    other_user = UserSerializer()
    # Minimal pet info {id, name}
    pet = serializers.SerializerMethodField()
    # Full pet details from the same 'pet' object the view provides
    pet_detail = PetSerializer(source='pet', read_only=True)
    latest_message = MessageSerializer(allow_null=True)
    unread_count = serializers.IntegerField()

    def get_pet(self, obj):
        """
        View passes a dict like:
          {
            'other_user': <User>,
            'pet': <Pet>,
            'latest_message': <Message>,
            'unread_count': <int>,
          }

        Since obj is a dict, we must access it safely.
        """
        pet = obj.get('pet') if isinstance(obj, dict) else getattr(obj, 'pet', None)
        if pet:
            return {'id': getattr(pet, 'id', None), 'name': getattr(pet, 'name', '')}
        return None