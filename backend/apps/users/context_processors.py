from django.conf import settings


def frontend_context(_request):
    return {
        'frontend_url': settings.FRONTEND_URL,
        'site_name': settings.SITE_NAME,
    }