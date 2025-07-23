from django.contrib import admin
from .models import CustomUser, VerificationRequest, Post

admin.site.register(CustomUser)
admin.site.register(VerificationRequest)
admin.site.register(Post)

