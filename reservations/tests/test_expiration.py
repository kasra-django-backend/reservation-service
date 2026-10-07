"""
Test: Reservation expiration.
"""
import pytest

from products.models import Product
from reservations.models import Reservation, ReservationStatus
from reservations.services import expire_pending_reservations


@pytest.mark.django_db
class TestExpiration:

    def test_expire_releases_stock(self, expired_reservation, product):
        """Expiring a pending reservation releases stock."""
        product.refresh_from_db()
        stock_before = product.stock

        count = expire_pending_reservations()
        assert count == 1

        expired_reservation.refresh_from_db()
        assert expired_reservation.status == ReservationStatus.EXPIRED

        product.refresh_from_db()
        assert product.stock == stock_before + expired_reservation.quantity

    def test_expire_skips_non_expired(self, reservation, product):
        """Non-expired PENDING reservations are not touched."""
        count = expire_pending_reservations()
        assert count == 0

        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.PENDING

    def test_confirm_after_expire_raises(self, api_client, expired_reservation, user):
        """Confirming an expired reservation returns 409."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = api_client.post(f"/api/reservations/{expired_reservation.id}/confirm/")
        assert response.status_code == 409
        assert response.json()["error"]["code"] in ("RESERVATION_EXPIRED", "INVALID_STATE_TRANSITION")