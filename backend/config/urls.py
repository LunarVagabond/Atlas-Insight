import json
import os

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponse
from django.urls import include, path
from ninja import NinjaAPI  # noqa: E402
from ninja.openapi.docs import Swagger, _csrf_needed, _render_cdn_template

from apps.api.router import router as api_router
from apps.repositories.router import router as repositories_router
from apps.repositories.router_contributors import router as contributors_router
from apps.users.router import router as auth_router
from config.error_views import (  # noqa: I001
    frontend_home_redirect,
    handler403 as custom_handler403,
    handler404 as custom_handler404,
    handler500 as custom_handler500,
)


class _CdnSwagger(Swagger):
    """Always render the CDN-hosted Swagger UI — avoids relying on collectstatic."""

    def render_page(self, request, api, **kwargs):
        self.settings['url'] = self.get_openapi_url(api, kwargs)
        context = {
            'swagger_settings': json.dumps(self.settings, indent=1),
            'api': api,
            'add_csrf': _csrf_needed(api),
        }
        return _render_cdn_template(request, self.template_cdn, context)


api = NinjaAPI(
    title='Atlas Insight API',
    version='1.0.0',
    description='Repository archaeology and static analysis platform.',
    docs_url='/docs',
    docs=_CdnSwagger(),
)
api.add_router('/v1/', api_router)
api.add_router('/v1/repositories/', repositories_router)
api.add_router('/v1/', contributors_router)
api.add_router('/v1/auth/', auth_router)

def _serve_favicon(request):
    favicon = settings.REPO_ROOT / 'frontend' / 'public' / 'favicon.ico'
    if os.path.exists(favicon):
        return FileResponse(open(favicon, 'rb'), content_type='image/x-icon')
    return HttpResponse(status=204)


urlpatterns = [
    path('favicon.ico', _serve_favicon),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('django_prometheus.urls')),
    path('api/', api.urls),
    path('', frontend_home_redirect),
]

handler403 = custom_handler403
handler404 = custom_handler404
handler500 = custom_handler500
