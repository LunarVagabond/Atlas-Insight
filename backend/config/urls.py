from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.api.router import router as api_router
from apps.repositories.router import router as repositories_router

api = NinjaAPI(
    title='Atlas Insight API',
    version='1.0.0',
    description='Repository archaeology and static analysis platform.',
)
api.add_router('/v1/', api_router)
api.add_router('/v1/repositories/', repositories_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
