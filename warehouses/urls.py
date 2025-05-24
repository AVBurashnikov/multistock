from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'warehouses', views.WarehouseViewSet, basename='warehouse')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'inventory', views.InventoryViewSet, basename='inventory')
router.register(r'transfers', views.TransferLogViewSet, basename='transfers')
# router.register(r'login', obtain_auth_token, basename='login')
urlpatterns = router.urls
