from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)

    class Meta:
        model = Order
        fields = ("id", "reservation_id", "status", "created_at")
        read_only_fields = fields