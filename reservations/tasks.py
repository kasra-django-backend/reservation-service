"""
Celery tasks for reservations.
"""
# بگو: "این تسک Celery هست. هر ۳۰ ثانیه صدا زده میشه و رزروهای منقضی رو expire میکنه."
# این فایل وظایف پس‌زمینه مربوط به رزروها را مدیریت می‌کند.
import logging
from celery import shared_task

from .services import expire_pending_reservations as _expire

logger = logging.getLogger(__name__)

# تابع زیر را به‌عنوان Task سلری با نام مشخص ثبت می‌کند.
@shared_task(name="reservations.tasks.expire_pending_reservations")
# تابعی که رزروهای در انتظار و منقضی‌شده را پردازش می‌کند.
def expire_pending_reservations():
    """Periodic task — expires overdue PENDING reservations."""
    # منطق انقضای رزروها را اجرا کرده و تعداد رزروهای منقضی‌شده را دریافت می‌کند.
    try:
        count = _expire()
        return {"expired": count}
    except Exception:
        logger.exception("Failed to expire pending reservations")
        raise
    # خطا را دوباره پرتاب می‌کند تا Celery متوجه شکست Task شود.