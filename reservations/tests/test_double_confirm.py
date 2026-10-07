"""
Test: Double confirm does not create two orders.
"""
import pytest
from rest_framework import status

from orders.models import Order


@pytest.mark.django_db
class TestDoubleConfirm:

    def test_confirm_twice_creates_one_order(self, auth_client, reservation):
        """Two confirms -> one Order, second returns 409."""
        url = f"/api/reservations/{reservation.id}/confirm/"

        r1 = auth_client.post(url)
        assert r1.status_code == status.HTTP_200_OK

        r2 = auth_client.post(url)
        assert r2.status_code == status.HTTP_409_CONFLICT
        assert r2.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

        assert Order.objects.filter(reservation=reservation).count() == 1