from django.core.serializers import serialize
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from warehouses.models import Warehouse, Product, Inventory
from warehouses.serializers import WarehouseSerializer, ProductSerializer, InventorySerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

    def create(self, request, *args, **kwargs):
        inventory, created = Inventory.objects.update_or_create(
            product=request.data['product'],
            warehouse=request.data['warehouse'],
            defaults={"quantity": request.data.get("quantity")},
            create_defaults=request.data
        )
        serializer = InventorySerializer(inventory)

        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="transfer")
    def transfer(self, request):
        product_id = request.data.get("product_id")
        from_warehouse_id = request.data.get("from_warehouse_id")
        to_warehouse_id = request.data.get("to_warehouse_id")
        quantity = request.data.get("quantity")

        if not all([product_id, from_warehouse_id, to_warehouse_id, quantity]):
            return Response(
                {"error": "Missing fields."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            return Response(
                {"error": "Quantity must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from_inventory = Inventory.objects.get(product_id=product_id, warehouse_id=from_warehouse_id)
        except Inventory.DoesNotExist:
            return Response(
                {"error": "No such product in source warehouse."},
                status=status.HTTP_404_NOT_FOUND
            )

        if from_inventory.quantity < quantity:
            return Response(
                {"error": "Not enough product in source warehouse."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Уменьшаем на складе-отправителе
        from_inventory.quantity -= quantity
        from_inventory.save()

        # Добавляем/обновляем на складе-получателе
        to_inventory, created = Inventory.objects.get_or_create(
            product_id=product_id,
            warehouse_id=to_warehouse_id,
            defaults={"quantity": 0}
        )
        to_inventory.quantity += quantity
        to_inventory.save()

        return Response({
            "message": "Transfer successful.",
            "transferred_quantity": quantity,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id
        }, status=status.HTTP_200_OK)

