from django.contrib import admin
from .models import Pet, PetImage, Payment

admin.site.register(Pet)
admin.site.register(PetImage)
admin.site.register(Payment)
