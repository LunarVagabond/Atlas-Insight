import logging

from ninja import Router

logger = logging.getLogger(__name__)

router = Router()


@router.get('/health', tags=['system'])
def health(request) -> dict:
    return {'status': 'ok', 'service': 'Atlas Insight API'}
