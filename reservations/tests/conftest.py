"""
Reservation-specific fixtures.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from reservations.models import Reservation, ReservationStatus
from reservations.services import create_reservation


@pytest.fixture
def reservation(user, product, db):
    """A PENDING reservation for `user` with quantity=2."""
    return create_reservation(user=user, product_id=product.id, quantity=2)


@pytest.fixture
def expired_reservation(user, product, db):
    """
    A PENDING reservation whose expires_at is already in the past.
    Created directly (not via service) so we can control expires_at.
    """
    product.refresh_from_db()
    r = Reservation.objects.create(
        user=user,
        product=product,
        quantity=1,
        status=ReservationStatus.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    # Decrement stock to mimic a real reservation
    product.stock -= 1
    product.save(update_fields=["stock"])
    return r