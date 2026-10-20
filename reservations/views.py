"""
Reservation API views.
"""
import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import DomainError
from .models import Reservation
from .serializers import ReservationCreateSerializer, ReservationSerializer
from . import services
from orders.serializers import OrderSerializer

logger = logging.getLogger(__name__)


class ReservationListCreateView(APIView):
    """
    POST /api/reservations/   — create a reservation
    GET  /api/reservations/   — list the current user's reservations
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Reservation.objects.filter(user=request.user).select_related("product")
        serializer = ReservationSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idempotency_key = request.headers.get("Idempotency-Key")

        try:
            reservation = services.create_reservation(     #رزرو ایجادشده را دریافت می‌کند
                user=request.user,
                product_id=data["product_id"],
                quantity=data["quantity"],
                idempotency_key=idempotency_key,
            )
        except DomainError as e:
            # Let the custom exception handler format it
            raise # خطا را دوباره پرتاب می‌کند تا مدیریت نهایی آن به Exception Handler واگذار شود.

        out = ReservationSerializer(reservation)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ReservationDetailView(APIView):
    """
    GET /api/reservations/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Reservation.objects.select_related("product").get(
                pk=pk, user=request.user
            )
        except Reservation.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Reservation not found.")

    def get(self, request, pk):
        reservation = self.get_object(request, pk)
        return Response(ReservationSerializer(reservation).data)
        # اطلاعات رزرو را سریالایز کرده و با پاسخ HTTP 200 برمی‌گرداند.


class ReservationConfirmView(APIView):
    """
    POST /api/reservations/{id}/confirm/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # سرویس تأیید رزرو را برای کاربر فعلی اجرا کرده و سفارش را دریافت می‌کند.
        order = services.confirm_reservation(user=request.user, reservation_id=pk)
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)


class ReservationCancelView(APIView):
    """
    POST /api/reservations/{id}/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        reservation = services.cancel_reservation(user=request.user, reservation_id=pk)
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_200_OK)