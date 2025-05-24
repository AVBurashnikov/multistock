import csv
from datetime import datetime, timezone

from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from warehouses.models import Warehouse, Product, Inventory, TransferLog, InventoryLog
from warehouses.serializers import WarehouseSerializer, ProductSerializer, InventorySerializer, TransferLogSerializer, \
    InventoryLogSerializer


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


    @action(detail=True, methods=['GET'], url_path='inventory/export')
    def warehouse_inventory_export(self, request, pk=None):
        inventories = Inventory.objects.filter(warehouse=pk).select_related('product')
        return self.csv_export(inventories, pk)


    @action(detail=False, methods=['GET'], url_path='inventory/export')
    def warehouse_inventory_export_all(self, request):
        inventories = Inventory.objects.all()
        return self.csv_export(inventories, many=True)


    def csv_export(self, inventories, warehouse_pk: int = 0, many:bool = False):
        response = HttpResponse(content_type='text/csv')
        if many:
            content_disposition = f'attachment; filename="warehouses_inventory_{datetime.now(timezone.utc).date().strftime("%d_%m_%Y")}.csv"'
        else:
            content_disposition = f'attachment; filename="warehouse_{warehouse_pk}_inventory_{datetime.now(timezone.utc).date().strftime("%d_%m_%Y")}.csv"'
        response['Content-Disposition'] = content_disposition
        writer = csv.writer(response)
        writer.writerow(['product', 'name', 'sku', 'quantity'])

        for inventory in inventories:
            writer.writerow([
                inventory.product.id,
                inventory.product.name,
                inventory.product.sku,
                inventory.quantity
            ])
        return response

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

    @action(detail=False, methods=['GET'], url_path='summary')
    def summary(self, request):
        # аггрегируем по ID продукта и считаем сумму продуктов на всех складах для групп
        aggregated = Inventory.objects.values("product").annotate(total_quantity=Sum("quantity"))

        products = {
            item.id: item
            for item in Product.objects.filter(id__in=[item["product"] for item in aggregated])
        }

        result = []
        for item in aggregated:
            product = products[item["product"]]
            result.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "total_quantity": item["total_quantity"]
                }
            )

        return Response(result)

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

    @action(detail=False, methods=['GET'], url_path='logs')
    def inventory_logs(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([start_date, end_date]) or start_date > end_date:
            inventory_logs = InventoryLog.objects.all()
        else:
            inventory_logs = InventoryLog.objects.filter(created_at__gte=start_date, created_at__lte=end_date)

        serializer = InventoryLogSerializer(inventory_logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class TransferLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransferLog.objects.all()
    serializer_class = TransferLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'from_warehouse', 'to_warehouse']
