"""
Test: Idempotency-Key behavior.
"""
import uuid
import pytest
from rest_framework import status

from products.models import Product
from reservations.models import Reservation


@pytest.mark.django_db
class TestIdempotency:

    def test_same_key_returns_same_reservation(self, auth_client, product):
        """Two POSTs with same Idempotency-Key -> one reservation."""
        key = str(uuid.uuid4())
        payload = {"product_id": product.id, "quantity": 1}
        headers = {"HTTP_IDEMPOTENCY_KEY": key}

        r1 = auth_client.post("/api/reservations/", payload, format="json", **headers)
        r2 = auth_client.post("/api/reservations/", payload, format="json", **headers)

        assert r1.status_code == status.HTTP_201_CREATED
        assert r2.status_code == status.HTTP_201_CREATED
        assert r1.json()["id"] == r2.json()["id"]

        assert Reservation.objects.count() == 1

    def test_same_key_does_not_decrement_twice(self, auth_client, product):
        """Stock should only decrease once for the same key."""
        initial = product.stock
        key = str(uuid.uuid4())
        payload = {"product_id": product.id, "quantity": 2}

        auth_client.post("/api/reservations/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)
        auth_client.post("/api/reservations/", payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

        product.refresh_from_db()
        assert product.stock == initial - 2

    def test_different_keys_create_different_reservations(self, auth_client, product):
        """Different keys -> different reservations."""
        payload = {"product_id": product.id, "quantity": 1}

        auth_client.post("/api/reservations/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        auth_client.post("/api/reservations/", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

        assert Reservation.objects.count() == 2