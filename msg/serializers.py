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
    pet_detail = PetSerializer(source='pet', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'receiver_detail', 'pet', 'pet_detail', 'content', 'timestamp', 'is_read']
        read_only_fields = ['sender', 'receiver_detail', 'timestamp', 'is_read']

class ConversationSerializer(serializers.Serializer):
    other_user = UserSerializer()
    pet = serializers.SerializerMethodField()
    pet_detail = PetSerializer()
    latest_message = MessageSerializer(allow_null=True)
    unread_count = serializers.IntegerField()

    def get_pet(self, obj):
        if obj.pet:
            return {'id': obj.pet.id, 'name': obj.pet.name}
        return None