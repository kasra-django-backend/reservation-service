"""
Test: Normal reservation flow.
"""
import pytest
from rest_framework import status

from products.models import Product
from reservations.models import Reservation, ReservationStatus


@pytest.mark.django_db
class TestNormalReservation:

    def test_create_reservation_via_api(self, auth_client, product):
        """POST /api/reservations/ creates a PENDING reservation and decrements stock."""
        initial_stock = product.stock
        payload = {"product_id": product.id, "quantity": 2}

        response = auth_client.post("/api/reservations/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == ReservationStatus.PENDING
        assert data["quantity"] == 2
        assert data["product"] == product.id

        product.refresh_from_db()
        assert product.stock == initial_stock - 2

        assert Reservation.objects.filter(status=ReservationStatus.PENDING).count() == 1

    def test_get_reservation(self, auth_client, reservation):
        """GET /api/reservations/{id}/ returns the reservation."""
        response = auth_client.get(f"/api/reservations/{reservation.id}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == reservation.id
        assert data["status"] == ReservationStatus.PENDING

    def test_list_reservations(self, auth_client, reservation):
        """GET /api/reservations/ lists only my reservations."""
        response = auth_client.get("/api/reservations/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

    def test_confirm_creates_order(self, auth_client, reservation):
        """POST /api/reservations/{id}/confirm/ creates an Order."""
        response = auth_client.post(f"/api/reservations/{reservation.id}/confirm/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "CREATED"
        assert data["reservation_id"] == reservation.id

        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CONFIRMED
    def test_cancel_releases_stock(self, auth_client, reservation, product):
        """POST /api/reservations/{id}/cancel/ releases stock."""
        # Refresh to get the current stock AFTER the reservation was created
        product.refresh_from_db()
        initial_stock = product.stock

        response = auth_client.post(f"/api/reservations/{reservation.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK

        product.refresh_from_db()
        assert product.stock == initial_stock + reservation.quantity
        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CANCELLED