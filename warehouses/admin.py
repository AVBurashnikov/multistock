from django.contrib import admin

from warehouses.models import Warehouse, Product, Inventory, TransferLog

# Register your models here.
admin.site.register(Warehouse)
admin.site.register(Product)
admin.site.register(Inventory)
admin.site.register(TransferLog)

