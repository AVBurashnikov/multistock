from itertools import product

from django.core.serializers import serialize
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from warehouses.models import Warehouse, Product, Inventory, TransferLog
from warehouses.serializers import WarehouseSerializer, ProductSerializer, InventorySerializer, TransferLogSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

    @action(detail=True, methods=['GET'], url_path='inventory')
    def warehouse_inventory(self, request, pk=None):
        search = request.query_params.get('search', '').lower()

        inventories = Inventory.objects.filter(warehouse=pk).select_related('product')

        if search:
            inventories = inventories.filter(product__name__icontains=search)

        data = [
            {
                "product_id": inventory.product.id,
                "name": inventory.product.name,
                "sku": inventory.product.sku,
                "quantity": inventory.quantity
            }
            for inventory in inventories
        ]
        return Response(data)


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
            TransferLog.objects.create(
                product=Product.objects.get(pk=product_id),
                from_warehouse=Warehouse.objects.get(pk=from_warehouse_id),
                to_warehouse=Warehouse.objects.get(pk=to_warehouse_id),
                quantity=quantity
            )
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


class TransferLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransferLog.objects.all()
    serializer_class = TransferLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'from_warehouse', 'to_warehouse']
