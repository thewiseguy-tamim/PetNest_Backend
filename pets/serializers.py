from django.db import transaction
from rest_framework import serializers
from .models import Pet, PetImage, Payment

class PetImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetImage
        fields = ['id', 'image', 'uploaded_at']

class PetSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    image = serializers.ImageField(write_only=True, required=True)
    images_data = serializers.SerializerMethodField()
    ref_name = 'PetsPetSerializer'

    class Meta:
        model = Pet
        fields = [
            'id', 'owner', 'name', 'pet_type', 'breed', 'age',
            'gender', 'description', 'is_for_adoption', 'price',
            'availability', 'created_at', 'updated_at',
            'image', 'images_data'
        ]

    def get_images_data(self, obj):
        if isinstance(obj, Pet) and obj.pk:
            return PetImageSerializer(obj.images.all(), many=True).data
        return []

    def validate(self, data):
        is_for_adoption = data.get('is_for_adoption', getattr(self.instance, 'is_for_adoption', False))
        price = data.get('price', getattr(self.instance, 'price', None) if self.instance else None)

        if is_for_adoption and price is not None:
            raise serializers.ValidationError({'price': 'Price is not allowed for adoption listings'})
        if not is_for_adoption:
            if price is None:
                raise serializers.ValidationError({'price': 'Price is required for sale listings'})
            if price <= 0:
                raise serializers.ValidationError({'price': 'Price must be a positive value for sale listings'})
        return data

    def create(self, validated_data):
        image = validated_data.pop('image')
        owner = self.context['request'].user
        validated_data.pop('owner', None)
        with transaction.atomic():
            pet = Pet.objects.create(owner=owner, **validated_data)
            PetImage.objects.create(pet=pet, image=image)
        return pet

    def update(self, instance, validated_data):
        image = validated_data.pop('image', None)
        replace_images = validated_data.pop('replace_images', False)
        with transaction.atomic():
            if image and replace_images:
                instance.images.all().delete()
                PetImage.objects.create(pet=instance, image=image)
            elif image:
                PetImage.objects.create(pet=instance, image=image)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        return instance

class PaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    post_id = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['id', 'user_name', 'pet_name', 'post_id', 'transaction_id', 'amount', 'status', 'created_at']

    def get_post_id(self, obj):
        from users.models import Post
        try:
            post = Post.objects.get(pet=obj.pet, user=obj.user)
            return post.id
        except Post.DoesNotExist:
            return None