"""
Celery tasks for reservations.
"""
import logging
from celery import shared_task

from .services import expire_pending_reservations as _expire

logger = logging.getLogger(__name__)


@shared_task(name="reservations.tasks.expire_pending_reservations")
def expire_pending_reservations():
    """Periodic task — expires overdue PENDING reservations."""
    try:
        count = _expire()
        return {"expired": count}
    except Exception:
        logger.exception("Failed to expire pending reservations")
        raise