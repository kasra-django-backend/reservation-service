"""
Test: Invalid state transitions.
"""
import pytest
from rest_framework import status

from reservations.models import Reservation, ReservationStatus


@pytest.mark.django_db
class TestInvalidTransitions:

    def test_cancel_confirmed_reservation_fails(self, auth_client, reservation):
        """PENDING -> CONFIRMED -> CANCELLED must fail."""
        # Confirm first
        auth_client.post(f"/api/reservations/{reservation.id}/confirm/")
        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CONFIRMED

        # Try cancel
        r = auth_client.post(f"/api/reservations/{reservation.id}/cancel/")
        assert r.status_code == status.HTTP_409_CONFLICT
        assert r.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    def test_confirm_cancelled_reservation_fails(self, auth_client, reservation):
        """CANCELLED -> CONFIRMED must fail."""
        auth_client.post(f"/api/reservations/{reservation.id}/cancel/")
        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CANCELLED

        r = auth_client.post(f"/api/reservations/{reservation.id}/confirm/")
        assert r.status_code == status.HTTP_409_CONFLICT

    def test_confirm_expired_reservation_fails(self, auth_client, expired_reservation):
        """EXPIRED -> CONFIRMED must fail."""
        # Trigger expiration via service (uses same user as auth_client)
        from reservations.services import expire_pending_reservations
        expire_pending_reservations()

        r = auth_client.post(f"/api/reservations/{expired_reservation.id}/confirm/")
        assert r.status_code == status.HTTP_409_CONFLICT