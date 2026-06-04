import sys as _sys_logging
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
CORS_ALLOW_CREDENTIALS = True  # NEVER set CORS_ALLOWED_ORIGINS to '*' with this enabled

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
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.users.context_processors.frontend_context',
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
SOCIALACCOUNT_LOGIN_ON_GET = False
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
EVICT_AFTER_HOURS = config('EVICT_AFTER_HOURS', default=24, cast=int)
MAX_CACHE_GB = config('MAX_CACHE_GB', default=10, cast=float)
LOG_RETENTION_DAYS = config('LOG_RETENTION_DAYS', default=30, cast=int)

# Logging

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


_service_name = _detect_service_name()

_LOG_HANDLERS = ['console']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
        },
    },
    'loggers': {
        'django': {'handlers': _LOG_HANDLERS, 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': _LOG_HANDLERS, 'level': 'ERROR', 'propagate': False},
        'django.server': {'handlers': _LOG_HANDLERS, 'level': 'ERROR', 'propagate': False},
        'django.template': {'handlers': _LOG_HANDLERS, 'level': 'ERROR', 'propagate': False},
        'django.db.backends': {'handlers': _LOG_HANDLERS, 'level': 'WARNING', 'propagate': False},
        'celery': {'handlers': _LOG_HANDLERS, 'level': LOG_LEVEL, 'propagate': False},
        'apps': {'handlers': _LOG_HANDLERS, 'level': LOG_LEVEL, 'propagate': False},
    },
    'root': {'handlers': _LOG_HANDLERS, 'level': LOG_LEVEL},
}

# Write to _running/logs/<service>.log when LOG_TO_FILE=True (truncate on each start).
# Independent of DEBUG — set True locally even with production settings.
LOG_TO_FILE = config('LOG_TO_FILE', default=False, cast=bool)
if LOG_TO_FILE:
    _log_dir = REPO_ROOT / '_running' / 'logs'
    _log_dir.mkdir(parents=True, exist_ok=True)
    LOGGING['handlers']['file'] = {
        'class': 'logging.FileHandler',
        'filename': str(_log_dir / f'{_service_name}.log'),
        'mode': 'w',
        'formatter': 'verbose',
    }
    _LOG_HANDLERS.append('file')
