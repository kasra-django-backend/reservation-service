from rest_framework import serializers
from .models import Reservation


class ReservationCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class ReservationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Reservation
        fields = (
            "id", "product", "product_name", "quantity",
            "status", "expires_at", "created_at",
        )
        read_only_fields = fields