import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='analysis.analyze_repository')
def analyze_repository(repository_id: int) -> dict:
    """Stub — see TASKS.md tasks #5–#10 for full implementation."""
    logger.info('analyze_repository queued for repository_id=%d', repository_id)
    return {'status': 'pending_implementation', 'repository_id': repository_id}
