from django.contrib import admin

from warehouses.models import Warehouse, Product, Inventory

# Register your models here.
admin.site.register(Warehouse)
admin.site.register(Product)
admin.site.register(Inventory)

