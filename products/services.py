"""
Product-related services.
"""
from decimal import Decimal
from .models import Product


def create_product(name: str, price: Decimal, stock: int) -> Product:
    """Create a product. Used in tests and admin tooling."""
    return Product.objects.create(name=name, price=price, stock=stock)