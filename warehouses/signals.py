from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from warehouses.models import Inventory, InventoryLog


@receiver(post_save, sender=Inventory)
def log_inventory_save(sender, instance, created, **kwargs):
    InventoryLog.objects.create(
        product=instance.product,
        warehouse=instance.warehouse,
        quantity=instance.quantity,
        operation='add' if created else 'update',
    )

@receiver(post_delete, sender=Inventory)
def log_inventory_delete(sender, instance, **kwargs):
    InventoryLog.objects.create(
        product=instance.product,
        warehouse=instance.warehouse,
        quantity=0,
        operation='remove'
    )