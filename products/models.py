from django.db import models

class Product(models.Model):
    """
   مرجع اصلی تشخیص موجودی است. stock این محصول موجودی محدودی دارد و مقدار 
    """
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} (stock={self.stock})"