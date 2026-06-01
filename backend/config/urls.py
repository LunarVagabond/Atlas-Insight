from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from ninja import NinjaAPI

from apps.api.router import router as api_router
from apps.repositories.router import router as repositories_router
from apps.users.router import router as auth_router

api = NinjaAPI(
    title='Atlas Insight API',
    version='1.0.0',
    description='Repository archaeology and static analysis platform.',
    docs_url='/api/docs',
)
api.add_router('/v1/', api_router)
api.add_router('/v1/repositories/', repositories_router)
api.add_router('/v1/auth/', auth_router)

urlpatterns = [
    path('favicon.ico', lambda r: HttpResponse(status=204)),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('api/', api.urls),
]
