"""
Root-level pytest fixtures shared across all apps.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    """Plain DRF API client."""
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Factory to create users on demand."""
    User = get_user_model()
    counter = {"n": 0}

    def _create(username=None, password="testpass123", **kwargs):
        counter["n"] += 1
        username = username or f"user_{counter['n']}"
        return User.objects.create_user(username=username, password=password, **kwargs)

    return _create


@pytest.fixture
def user(user_factory):
    """A single default user."""
    return user_factory(username="defaultuser")


@pytest.fixture
def auth_client(api_client, user):
    """API client authenticated as `user` via JWT."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def other_user(user_factory):
    """A second user for authorization tests."""
    return user_factory(username="otheruser")


@pytest.fixture
def other_auth_client(api_client, other_user):
    """API client authenticated as `other_user`."""
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def product_factory(db):
    """Factory to create products on demand."""
    from products.models import Product
    counter = {"n": 0}

    def _create(name=None, price="499.99", stock=10, **kwargs):
        counter["n"] += 1
        name = name or f"Product_{counter['n']}"
        return Product.objects.create(name=name, price=price, stock=stock, **kwargs)

    return _create


@pytest.fixture
def product(product_factory):
    """A single product with stock=10."""
    return product_factory(name="TestPS5", stock=10)