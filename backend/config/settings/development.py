from decouple import config

from .base import *  # noqa: F401, F403

# Keep development mode default behavior while allowing .env overrides.
DEBUG = config('DEBUG', default=True, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-not-for-production')
ALLOWED_HOSTS = ['*']

LOGGING['loggers']['apps']['level'] = 'DEBUG'  # noqa: F405
LOGGING['loggers']['django']['level'] = 'DEBUG'  # noqa: F405
