import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from django.conf import settings
from ninja import Router, Schema
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

router = Router()

_STARTED_AT = time.monotonic()

_DOC_SLUGS: dict[str, Path] = {
    'api': settings.BASE_DIR / 'docs' / 'api' / 'reference.md',
    'webhooks': settings.BASE_DIR / 'docs' / 'webhooks.md',
}


class ServiceStatus(Schema):
    ok: bool
    error: Optional[str] = None


class HealthOut(Schema):
    status: str
    service: str
    version: str
    uptime_seconds: float
    timestamp: str
    db: ServiceStatus
    redis: ServiceStatus


class DocOut(Schema):
    slug: str
    title: str
    content: str


@router.get('/health', tags=['system'], response=HealthOut)
def health(request):
    from django.db import connection

    db_status = ServiceStatus(ok=True)
    try:
        connection.ensure_connection()
    except Exception as exc:
        db_status = ServiceStatus(ok=False, error=str(exc))

    redis_status = ServiceStatus(ok=True)
    try:
        from django.core.cache import cache
        cache.set('_health_probe', 1, timeout=5)
        if cache.get('_health_probe') != 1:
            redis_status = ServiceStatus(ok=False, error='probe value mismatch')
    except Exception as exc:
        redis_status = ServiceStatus(ok=False, error=str(exc))

    all_ok = db_status.ok and redis_status.ok

    return HealthOut(
        status='ok' if all_ok else 'degraded',
        service='Atlas Insight API',
        version=getattr(settings, 'APP_VERSION', '1.0.0'),
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        db=db_status,
        redis=redis_status,
    )


@router.get('/docs/{slug}', tags=['system'], response=DocOut)
def get_doc(request, slug: str):
    path = _DOC_SLUGS.get(slug)
    if path is None or not path.exists():
        raise HttpError(404, f'Doc not found: {slug}')

    content = path.read_text(encoding='utf-8')
    first_line = content.lstrip().splitlines()[0] if content.strip() else slug
    title = first_line.lstrip('#').strip()

    return DocOut(slug=slug, title=title, content=content)
