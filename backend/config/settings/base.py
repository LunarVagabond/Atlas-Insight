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
]

MIDDLEWARE = [
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
REPO_CACHE_DIR = BASE_DIR.parent / config('REPO_CACHE_DIR', default='_running/repo_cache')
STALE_AFTER_DAYS = config('STALE_AFTER_DAYS', default=7, cast=int)
LOG_LEVEL = config('LOG_LEVEL', default='INFO')

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
}

RUNS_TO_KEEP_PER_REPO = config('RUNS_TO_KEEP_PER_REPO', default=10, cast=int)
EVICT_AFTER_DAYS = config('EVICT_AFTER_DAYS', default=30, cast=int)
LOG_RETENTION_DAYS = config('LOG_RETENTION_DAYS', default=30, cast=int)

# Logging
LOG_DIR = REPO_ROOT / '_running' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

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
        'django_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'celery_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'celery.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'django_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['django_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['django_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['django_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'django_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}
