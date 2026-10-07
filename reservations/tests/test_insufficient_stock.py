"""
Test: Insufficient stock handling.
"""
import pytest
from rest_framework import status

from products.models import Product
from reservations.models import Reservation


@pytest.mark.django_db
class TestInsufficientStock:

    def test_reject_when_quantity_exceeds_stock(self, auth_client, product):
        """Requesting more than available stock returns 409 + INSUFFICIENT_STOCK."""
        initial_stock = product.stock
        payload = {"product_id": product.id, "quantity": initial_stock + 1}

        response = auth_client.post("/api/reservations/", payload, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        body = response.json()
        assert body["error"]["code"] == "INSUFFICIENT_STOCK"

        # Stock unchanged
        product.refresh_from_db()
        assert product.stock == initial_stock
        assert Reservation.objects.count() == 0

    def test_reject_when_stock_is_zero(self, auth_client, product):
        """Zero stock -> 409."""
        product.stock = 0
        product.save(update_fields=["stock"])

        payload = {"product_id": product.id, "quantity": 1}
        response = auth_client.post("/api/reservations/", payload, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    def test_exact_stock_is_allowed(self, auth_client, product):
        """Requesting exactly the available stock should succeed."""
        initial_stock = product.stock
        payload = {"product_id": product.id, "quantity": initial_stock}

        response = auth_client.post("/api/reservations/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        product.refresh_from_db()
        assert product.stock == 0
