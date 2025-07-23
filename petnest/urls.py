from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Define the schema view for Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="PetNest API",
        default_version='v1',
        description="API documentation for PetNest, a platform for pet listings and messaging.",
        terms_of_service="",
        contact=openapi.Contact(email="nottamimislam@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def home(request):
    return JsonResponse({"message": "Welcome to PetNest! Visit /pets/ for pet listings."})

urlpatterns = [
    path('', home, name='home'),  # Handle root URL
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('pets/', include('pets.urls')),
    path('users/', include('users.urls')),
    path('messenger/', include('msg.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # Add Swagger UI
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),  # Add ReDoc UI
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)