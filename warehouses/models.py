from django.db import models

# Create your models here.
class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=100, unique=True)
    warehouses = models.ManyToManyField(Warehouse, through='Inventory')

    def __str__(self):
        return self.name


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
        
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name} = {self.quantity}"


class TransferLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='from_warehouse')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='to_warehouse')
    quantity = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} @ {self.from_warehouse.name} --> {self.to_warehouse} = {self.quantity}"