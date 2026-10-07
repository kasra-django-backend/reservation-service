from django.contrib import admin
from .models import Reservation, IdempotencyKey


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "quantity", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "product__name")


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "key", "reservation", "created_at")