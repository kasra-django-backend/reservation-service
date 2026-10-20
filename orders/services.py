"""
Order services.
"""
import logging
from django.db import transaction

from config.exceptions import InvalidStateTransitionError
from .models import Order, OrderStatus

logger = logging.getLogger(__name__)


@transaction.atomic
# لغو سفارش کاربر با شناسه مشخص
def cancel_order(*, user, order_id: int) -> Order:
    """
    Cancel an order. Only allowed from CREATED.
    (This is minimal — task doesn't require order cancellation, but state
     transitions should still be guarded.)
    """
    try:
        order = Order.objects.select_for_update().get(pk=order_id, user=user)
    except Order.DoesNotExist:
        raise InvalidStateTransitionError(message="Order not found.")

    if order.status != OrderStatus.CREATED:
        raise InvalidStateTransitionError(
            message=f"Cannot cancel order in status {order.status}."
        )

    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status"])
    logger.info("Order cancelled: id=%s user=%s", order.id, user.id)
    return order