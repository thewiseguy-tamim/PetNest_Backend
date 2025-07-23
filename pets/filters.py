from django_filters import rest_framework as filters
from django.db import models
from .models import Pet

class PetFilter(filters.FilterSet):
    keyword = filters.CharFilter(method='filter_by_keyword')
    pet_type = filters.ChoiceFilter(choices=Pet.PET_TYPES)
    gender = filters.ChoiceFilter(choices=Pet.GENDER_CHOICES)
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_age = filters.NumberFilter(field_name='age', lookup_expr='gte')
    max_age = filters.NumberFilter(field_name='age', lookup_expr='lte')
    breed = filters.CharFilter(lookup_expr='icontains')
    availability = filters.BooleanFilter(field_name='availability')

    class Meta:
        model = Pet
        fields = ['pet_type', 'gender', 'min_price', 'max_price', 'min_age', 'max_age', 'breed', 'availability']

    def filter_by_keyword(self, queryset, name, value):
        return queryset.filter(
            models.Q(name__icontains=value) |
            models.Q(breed__icontains=value) |
            models.Q(description__icontains=value)
        )