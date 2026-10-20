"""
Reservation services — the heart of the project.

Handles:
- Concurrency-safe stock reservation (SELECT ... FOR UPDATE)
- Idempotency via Idempotency-Key header
- State transitions (PENDING -> CONFIRMED | CANCELLED | EXPIRED)
- Expiration logic
"""
import logging
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone

from config.exceptions import (
    InsufficientStockError,
    InvalidStateTransitionError,
    ReservationExpiredError,
    IdempotencyConflictError,
)
from products.models import Product
from .models import Reservation, ReservationStatus, IdempotencyKey

logger = logging.getLogger(__name__)

RESERVATION_TTL_MINUTES = getattr(settings, "RESERVATION_TTL_MINUTES", 10)


# ============================================================
# State transition map — single source of truth
# ============================================================
# دیکشنری که مشخص می‌کند از هر وضعیت به چه وضعیتی می‌توان رفت.
ALLOWED_TRANSITIONS = {
    ReservationStatus.PENDING: {
        ReservationStatus.CONFIRMED,
        ReservationStatus.CANCELLED,
        ReservationStatus.EXPIRED,
    },
    ReservationStatus.CONFIRMED: set(),
    ReservationStatus.EXPIRED: set(),
    ReservationStatus.CANCELLED: set(),
}

# تابعی که چک می‌کند آیا ترنزیشن مجاز است یا نه.
def _assert_transition(current: str, target: str) -> None:
    """Raise if transition is not allowed."""
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        # اگر ترنزیشن در نقشه مجاز نبود..
        logger.warning(
            "Invalid state transition attempted: %s -> %s (reservation_id=%s)",
            current, target, getattr(_assert_transition, "_current_id", "?"),
        )
        # لاگ هشدار برای ترنزیشن غیرمجاز ثبت می‌شود.
        raise InvalidStateTransitionError(
            message=f"Cannot transition from {current} to {target}."
        )
        # خطای ترنزیشن نامعتبر پرتاب می‌شود.


# ============================================================
# IDEMPOTENCY
# ============================================================
# تشخیص می‌دهد آیا این درخواست تکراری است یا نه؛ خروجی: رکورد کلید + رزرو موجود.
def _resolve_idempotency(
    user, key: str | None, request_fingerprint: dict
) -> tuple[IdempotencyKey | None, Reservation | None]:
    # خروجی تابع یک رکورد کلید و یک رزرو موجوده که هرکدوم می‌تونن None باشن
    """
    Returns (record, existing_reservation).

    - If key is None → (None, None)
    - If key exists and has a reservation → (record, reservation) — replay
    - If key exists but no reservation → raise conflict (in-flight)
    - If key doesn't exist → create record atomically
    """
    if not key:
        return None, None

    try:
        uuid_key = UUID(str(key))
    except (ValueError, TypeError):
        raise IdempotencyConflictError(message="Idempotency-Key must be a valid UUID.")
        # خطای اختصاصی ایجاد می‌کنه که می‌گه کلید باید UUID معتبر باشه.

    try:
        with transaction.atomic():
            # یک تراکنش دیتابیس شروع می‌کنه تا عملیات داخلش به‌صورت اتمیک انجام بشه.
            record = IdempotencyKey.objects.create(
                user=user,
                key=uuid_key,
                response_body=request_fingerprint,
            )
        logger.info("Idempotency key registered: user=%s key=%s", user.id, uuid_key)
        return record, None
        # رکورد جدید رو برمی‌گردونه و اعلام می‌کنه رزرو قبلی پیدا نشده.

    except IntegrityError:
        # Key already exists — check if it has a reservation
        # اگر ایجاد رکورد به‌خاطر خطای یکپارچگی دیتابیس، مثلاً تکراری بودن ترکیب کاربر و کلید، شکست بخوره، خطا رو می‌گیره.
        record = IdempotencyKey.objects.select_for_update().get(
            user=user, key=uuid_key
        )
        if record.reservation_id:
            logger.info(
                "Idempotency replay: user=%s key=%s -> reservation=%s",
                user.id, uuid_key, record.reservation_id,
                # استفاده مجدد از کلیدی که رزرو داره رو در لاگ ثبت می‌کنه
            )
            return record, record.reservation
        # رکورد کلید و رزرو قبلی رو برمی‌گردونه تا رزرو تکراری ساخته نشه.
        # In-flight (another request holds the key but hasn't finished)
        logger.warning("Idempotency in-flight conflict: user=%s key=%s", user.id, uuid_key)
        raise IdempotencyConflictError()
        # خطای تعارض ایجاد می‌کنه، چون درخواست قبلی با همین کلید هنوز نتیجه نهایی نداره.


# ============================================================
# CREATE RESERVATION
# ============================================================
# تمام عملیات دیتابیس این تابع رو در یک تراکنش قرار می‌ده تا در صورت خطا، تغییرات انجام‌شده در تراکنش برگردونده بشن؛ به این می‌گن Atomicity.
@transaction.atomic
def create_reservation(
    *,
    user,
    product_id: int,
    quantity: int,
    idempotency_key: str | None = None,
) -> Reservation:
    """
    Create a reservation with concurrency safety and idempotency.

    Steps:
    1. Resolve idempotency (may return existing reservation)
    2. Lock the product row (SELECT FOR UPDATE)
    3. Check stock
    4. Create reservation
    5. Link to idempotency record
    """
    fingerprint = {"product_id": product_id, "quantity": quantity}
    record, existing = _resolve_idempotency(user, idempotency_key, fingerprint)
    # کلید درخواست رو بررسی می‌کنه تا مشخص بشه درخواست قبلاً پردازش شده یا نه.

    if existing is not None:
        return existing
    # اگر رزرو قبلی وجود داشته باشه، همون رو برمی‌گردونه و رزرو جدیدی نمی‌سازه.
    # --- Lock the product row to prevent overselling ---
    try:
        product = (
            Product.objects.select_for_update()
            .get(pk=product_id)
        )
    except Product.DoesNotExist:
        raise InsufficientStockError(message="Product not found.")

    if product.stock < quantity:
        logger.warning(
            "Reservation rejected: insufficient stock. user=%s product=%s requested=%s available=%s",
            # قالب پیام هشدار رو مشخص می‌کنه که اطلاعات درخواست و موجودی رو ثبت می‌کنه.
            user.id, product_id, quantity, product.stock,
        )
        raise InsufficientStockError(
            message=f"Requested quantity is not available. Available: {product.stock}."
        )

    # --- Decrement stock atomically ---
    # موجودی محصول رو به‌اندازه تعداد رزروشده کاهش می‌ده.
    product.stock -= quantity
    product.save(update_fields=["stock"])

    # --- Create reservation ---
    now = timezone.now()
    reservation = Reservation.objects.create(
        user=user,
        product=product,
        quantity=quantity,
        status=ReservationStatus.PENDING,
        # زمان انقضای رزرو رو با اضافه کردن مدت اعتبار به زمان فعلی محاسبه می‌کنه.
        expires_at=now + timedelta(minutes=RESERVATION_TTL_MINUTES),
    )

    # --- Link to idempotency record ---
    # بررسی می‌کنه آیا برای درخواست، رکورد Idempotency ساخته شده.
    if record is not None:
        # رزرو جدید رو به رکورد Idempotency مرتبط می‌کنه.
        record.reservation = reservation
        record.response_status = 201
        record.save(update_fields=["reservation", "response_status"])

    logger.info(
        "Reservation created: id=%s user=%s product=%s qty=%s expires_at=%s",
        reservation.id, user.id, product_id, quantity, reservation.expires_at,
    )
    return reservation


# ============================================================
# CONFIRM RESERVATION
# ============================================================
@transaction.atomic
def confirm_reservation(*, user, reservation_id: int):
    """
    Confirm a reservation -> creates exactly one Order.
    Uses SELECT FOR UPDATE on the reservation to prevent double-confirm.
    """
    try:
        reservation = (
            Reservation.objects.select_for_update()
            .select_related("product")
            .get(pk=reservation_id, user=user)
        )
    except Reservation.DoesNotExist:
        raise InvalidStateTransitionError(message="Reservation not found.")

    # Late expiry check
    if reservation.status == ReservationStatus.PENDING and reservation.is_expired:
        # رزرو رو منقضی می‌کنه و موجودی محصول رو آزاد می‌کنه.
        _expire_locked(reservation)
        raise ReservationExpiredError()

    # بررسی می‌کنه تغییر وضعیت فعلی رزرو به CONFIRMED مجاز باشه.
    _assert_transition(reservation.status, ReservationStatus.CONFIRMED)

    # Late import to avoid circulars
    from orders.models import Order, OrderStatus

    # OneToOneField guarantees only one order can exist
    # سفارش مرتبط رو پیدا می‌کنه یا اگر وجود نداشته باشه، ایجادش می‌کنه.
    order, created = Order.objects.get_or_create(
        reservation=reservation,
        defaults={"user": user, "status": OrderStatus.CREATED},
    )
    if not created:
        logger.info("Order already exists for reservation=%s (idempotent confirm)", reservation.id)
    else:
        logger.info("Order created: id=%s reservation=%s", order.id, reservation.id)

    reservation.status = ReservationStatus.CONFIRMED
    reservation.save(update_fields=["status", "updated_at"])

    return order
    # سفارش ایجادشده یا سفارش موجود رو برمی‌گردونه


# ============================================================
# CANCEL RESERVATION
# ============================================================
@transaction.atomic

# هدف تابع، لغو رزرو در انتظار و آزاد کردن موجودی است.
def cancel_reservation(*, user, reservation_id: int) -> Reservation:
    """Cancel a PENDING reservation and release stock."""
    try:
        reservation = (
            Reservation.objects.select_for_update()
            .select_related("product")
            .get(pk=reservation_id, user=user)
        )
    except Reservation.DoesNotExist:
        raise InvalidStateTransitionError(message="Reservation not found.")

    if reservation.status == ReservationStatus.PENDING and reservation.is_expired:
        _expire_locked(reservation)
        # موجودی را برمی‌گرداند
        raise ReservationExpiredError()
    
    # لغو رزرو از وضعیت فعلی مجاز باشد
    _assert_transition(reservation.status, ReservationStatus.CANCELLED)

    # Release stock
    # آزاد کردن موجودی
    product = Product.objects.select_for_update().get(pk=reservation.product_id)
    product.stock += reservation.quantity
    product.save(update_fields=["stock"])

    reservation.status = ReservationStatus.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])

    logger.info(
        "Reservation cancelled: id=%s user=%s released=%s new_stock=%s",
        reservation.id, user.id, reservation.quantity, product.stock,
    )
    return reservation


# ============================================================
# EXPIRATION
# ============================================================
# تابعی برای منقضی کردن رزرو و آزاد کردن موجودی است.
def _expire_locked(reservation: Reservation) -> None:
    """Expire a reservation assumed already locked. Releases stock."""
    #   رزرو از قبل قفل شده و موجودی آن باید آزاد شود

    product = Product.objects.select_for_update().get(pk=reservation.product_id)
    product.stock += reservation.quantity
    product.save(update_fields=["stock"])

    reservation.status = ReservationStatus.EXPIRED
    reservation.save(update_fields=["status", "updated_at"])
    logger.info(
        "Reservation expired: id=%s user=%s released=%s new_stock=%s",
        reservation.id, reservation.user_id, reservation.quantity, product.stock,
    )

# تابعی برای منقضی کردن گروهی رزروهای منقضی‌شده است و تعدادشان را برمی‌گرداند.
def expire_pending_reservations() -> int:
    """
    Batch-expire overdue PENDING reservations.
    Called by Celery Beat periodically.
    """
    now = timezone.now()
    overdue_ids = list(
        Reservation.objects.filter(
            status=ReservationStatus.PENDING,
            expires_at__lte=now,
            # زروهایی را انتخاب می‌کند که زمان انقضایشان گذشته یا برابر زمان فعلی است
        ).values_list("id", flat=True)
    )
    count = 0
    for rid in overdue_ids:
        try:
            with transaction.atomic():
                # عملیات مربوط به هر رزرو را در یک تراکنش جداگانه انجام می‌دهد.
                reservation = (
                    Reservation.objects.select_for_update()
                    .select_related("product")
                    .get(pk=rid)
                )
                if reservation.status != ReservationStatus.PENDING:
                    continue
                if reservation.expires_at > timezone.now():
                    continue
                _expire_locked(reservation)
                # رزرو را منقضی می‌کند و موجودی محصول را آزاد می‌کند
                count += 1
        except Reservation.DoesNotExist:
            continue
        
    # حداقل یک رزرو منقضی شده باشد
    if count:
        logger.info("Expired %s reservation(s)", count)
    return count