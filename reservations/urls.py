from django.urls import path
from .views import (
    ReservationListCreateView,
    ReservationDetailView,
    ReservationConfirmView,
    ReservationCancelView,
)

urlpatterns = [
    path("", ReservationListCreateView.as_view(), name="reservation-list-create"),
    path("<int:pk>/", ReservationDetailView.as_view(), name="reservation-detail"),
    path("<int:pk>/confirm/", ReservationConfirmView.as_view(), name="reservation-confirm"),
    path("<int:pk>/cancel/", ReservationCancelView.as_view(), name="reservation-cancel"),
]