from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

GITHUB_WEBHOOK_SECRET = config('GITHUB_WEBHOOK_SECRET')
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

# Override DB and cache with no fallback — missing vars crash on startup
DATABASES['default'].update({
    'NAME': config('POSTGRES_DB'),
    'USER': config('POSTGRES_USER'),
    'PASSWORD': config('POSTGRES_PASSWORD'),
    'HOST': config('POSTGRES_HOST'),
    'PORT': config('POSTGRES_PORT'),
})
CACHES['default']['LOCATION'] = config('REDIS_URL')
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
