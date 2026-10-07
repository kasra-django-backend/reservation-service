from django.db import models

from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    CANCELLED = "CANCELLED", "Cancelled"


class Order(models.Model):
    """
    Created when a Reservation is confirmed.
    One-to-one with Reservation ensures double-confirm cannot create two orders.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    reservation = models.OneToOneField(
        "reservations.Reservation",
        on_delete=models.PROTECT,
        related_name="order",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"Order#{self.pk} user={self.user_id} reservation={self.reservation_id}"