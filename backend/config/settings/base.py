from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='ai-api.dsyndicate.dev,atlas.dsyndicate.dev,ai-flower.dsyndicate.dev,localhost,127.0.0.1',
    cast=Csv(),
)

SITE_NAME = config('SITE_NAME', default='Atlas Insight')

# ── CORS / CSRF ──────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://atlas.dsyndicate.dev,http://localhost:4501',
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://atlas.dsyndicate.dev,https://ai-api.dsyndicate.dev,http://localhost:4501,http://localhost:4500',
    cast=Csv(),
)

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'ninja',
    'apps.users.apps.UsersConfig',
    'apps.repositories.apps.RepositoriesConfig',
    'apps.analysis.apps.AnalysisConfig',
    'apps.api.apps.ApiConfig',
    'django_celery_results',
    'django_celery_beat',
    'django_ratelimit',
    'django_prometheus',
]

SILENCED_SYSTEM_CHECKS = ['django_ratelimit.W001']

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'apps.users.middleware.OAuthCallbackHostMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Custom user model ────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'

# ── django-allauth ───────────────────────────────────────────────────────────
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': config('GITHUB_CLIENT_ID', default=''),
            'secret': config('GITHUB_CLIENT_SECRET', default=''),
            'key': '',
        },
        'SCOPE': ['read:user', 'user:email', 'repo'],
    }
}

ACCOUNT_LOGIN_METHODS = {'username'}
ACCOUNT_SIGNUP_FIELDS = ['username*', 'password1*', 'password2*']
ACCOUNT_DEFAULT_HTTP_PROTOCOL = config('ACCOUNT_DEFAULT_HTTP_PROTOCOL', default='https')
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

FRONTEND_URL = config('FRONTEND_URL', default='https://atlas.dsyndicate.dev')
BACKEND_URL = config('BACKEND_URL', default='https://ai-api.dsyndicate.dev')

# Share session + CSRF cookies across all *.dsyndicate.dev subdomains so the
# OAuth state set during login (atlas.dsyndicate.dev) is readable at the callback
# (ai-api.dsyndicate.dev). Falls back to None (host-only) for localhost dev.
_COOKIE_DOMAIN = config('SESSION_COOKIE_DOMAIN', default='.dsyndicate.dev') or None
SESSION_COOKIE_DOMAIN = _COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = _COOKIE_DOMAIN
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
LOGIN_REDIRECT_URL = FRONTEND_URL + '/?login=success'
LOGOUT_REDIRECT_URL = FRONTEND_URL

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='atlas_insight'),
        'USER': config('POSTGRES_USER', default='atlas'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='atlas_secret'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': config('POSTGRES_PORT', default='4503'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

GITHUB_TOKEN = config('GITHUB_TOKEN', default='')
GITHUB_WEBHOOK_SECRET = config('GITHUB_WEBHOOK_SECRET', default='')
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')
FEATURED_REPO_URL = config('FEATURED_REPO_URL', default='')
REPO_CACHE_DIR = BASE_DIR.parent / config('REPO_CACHE_DIR', default='_running/repo_cache')
STALE_AFTER_DAYS = config('STALE_AFTER_DAYS', default=7, cast=int)
LOG_LEVEL = config('LOG_LEVEL', default='INFO')

# Cache — Redis db 1 (Celery uses db 0)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:4502/1'),
    }
}

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:4502/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat — periodic tasks
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'cleanup-never-succeeded-repos': {
        'task': 'apps.analysis.tasks.cleanup_never_succeeded_repos',
        'schedule': crontab(minute=0),  # every hour
    },
    'check-stale-repos': {
        'task': 'apps.analysis.tasks.check_stale_repos',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'cleanup-old-runs': {
        'task': 'apps.analysis.tasks.cleanup_old_runs',
        'schedule': crontab(minute=30, hour=2),  # daily at 02:30 UTC
    },
    'evict-stale-clones': {
        'task': 'apps.analysis.tasks.evict_stale_clones',
        'schedule': crontab(minute=0, hour=3),  # daily at 03:00 UTC
    },
    'cleanup-old-logs': {
        'task': 'apps.analysis.tasks.cleanup_old_logs',
        'schedule': crontab(minute=30, hour=3),  # daily at 03:30 UTC
    },
    'select-repo-of-week': {
        'task': 'apps.analysis.tasks.select_repo_of_week',
        'schedule': crontab(minute=0, hour=0, day_of_week=1),  # Monday 00:00 UTC
    },
    'reanalyze-watched-repos': {
        'task': 'apps.analysis.tasks.reanalyze_watched_repos',
        'schedule': crontab(minute=0, hour=4),  # daily at 04:00 UTC
    },
}

RUNS_TO_KEEP_PER_REPO = config('RUNS_TO_KEEP_PER_REPO', default=10, cast=int)
EVICT_AFTER_DAYS = config('EVICT_AFTER_DAYS', default=30, cast=int)
LOG_RETENTION_DAYS = config('LOG_RETENTION_DAYS', default=30, cast=int)

# Logging
import sys as _sys_logging


def _detect_service_name() -> str:
    explicit = config('ATLAS_SERVICE', default='').strip()
    if explicit:
        return explicit

    argv = ' '.join(_sys_logging.argv).lower()
    if 'flower' in argv:
        return 'celery-flower'
    if 'celery' in argv and ' beat' in argv:
        return 'celery-beat'
    if 'celery' in argv:
        return 'celery-workers'
    return 'django'


_sentry_service = _detect_service_name()

# Add new Django app-level service buckets here.
_DJANGO_APP_SERVICE_MAP = {
    'analysis': 'django-analysis',
    'api': 'django-api',
    'repositories': 'django-repositories',
    'users': 'django-users',
    'utils': 'django-utils',
}


def _service_from_logger_name(logger_name: str) -> str:
    logger_name = (logger_name or '').strip()
    if logger_name:
        if logger_name.startswith('apps.'):
            parts = logger_name.split('.')
            app = parts[1] if len(parts) > 1 else ''
            if app in _DJANGO_APP_SERVICE_MAP:
                return _DJANGO_APP_SERVICE_MAP[app]
            return 'django'

        root = logger_name.split('.')[0]
        if root == 'config':
            return 'django-config'
        if root == 'django':
            return 'django'
        if root in {'flower'}:
            return 'celery-flower'
        if root in {'celery', 'kombu'}:
            return 'celery-workers'
    return _sentry_service

class _SentryServiceFilter:
    def filter(self, record):
        service_name = _service_from_logger_name(getattr(record, 'name', ''))
        setattr(record, 'service', service_name)
        # Forward to Sentry/GlitchTip if DSN is configured
        if SENTRY_DSN:
            try:
                import sentry_sdk
                message = record.getMessage()
                # Attach service context and send as explicit log capture
                with sentry_sdk.configure_scope() as scope:
                    scope.set_tag('service', service_name)
                    scope.set_context('service', {'name': service_name})
                    # Capture at appropriate level
                    if record.levelno >= 40:
                        sentry_sdk.capture_message(message, level='error')
                    elif record.levelno >= 30:
                        sentry_sdk.capture_message(message, level='warning')
                    else:
                        sentry_sdk.capture_message(message, level='info')
            except Exception:
                pass
        return True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sentry_service': {
            '()': _SentryServiceFilter,
        },
    },
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname:<8} {name} — {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['sentry_service'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

# ── Sentry / GlitchTip ───────────────────────────────────────────────────────
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import logging as _logging
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    def _derive_sentry_service(event: dict) -> str:
        logger_name = (event.get('logger') or '').strip()
        if logger_name:
            return _service_from_logger_name(logger_name)

        tx_name = (event.get('transaction') or '').strip()
        if tx_name.startswith('apps.'):
            parts = tx_name.split('.')
            app = parts[1] if len(parts) > 1 else ''
            if app in _DJANGO_APP_SERVICE_MAP:
                return _DJANGO_APP_SERVICE_MAP[app]
            return 'django'
        if tx_name.startswith('config.'):
            return 'django-config'

        return _sentry_service

    def _attach_service_fields(event: dict) -> dict:
        service_name = _derive_sentry_service(event)

        tags = dict(event.get('tags') or {})
        tags['service'] = service_name
        event['tags'] = tags

        contexts = dict(event.get('contexts') or {})
        service_ctx = dict(contexts.get('service') or {})
        service_ctx['name'] = service_name
        contexts['service'] = service_ctx
        event['contexts'] = contexts

        return event

    def _before_send(event, hint):
        return _attach_service_fields(event)

    def _before_send_transaction(event, hint):
        return _attach_service_fields(event)

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=config('DJANGO_SETTINGS_MODULE', default='development').split('.')[-1],
        server_name=_sentry_service,
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=_before_send,
        before_send_transaction=_before_send_transaction,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            # Disabled: LoggingIntegration may interfere with handler filters
            # LoggingIntegration(
            #     sentry_logs_level=_logging.INFO,
            #     event_level=None,
            #     level=_logging.INFO,
            # ),
        ],
        enable_logs=True,
    )

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag('service', _sentry_service)
        scope.set_context('service', {'name': _sentry_service})
