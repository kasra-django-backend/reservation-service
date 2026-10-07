from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductSerializer


class ProductListView(APIView):
    """GET /api/products/ — list all products."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Product.objects.all()
        return Response(ProductSerializer(qs, many=True).data)