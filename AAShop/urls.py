from django.urls import path, include
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, OrderViewSet, UserViewSet, initiate_payment, verify_payment, register_user, add_to_cart, view_cart, update_cart_item, remove_cart_item, payment_success
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def payment_success(request):
    return HttpResponse("✅ Payment was successful!")

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),

    # User registration endpoint
    path("api/register/", register_user, name="register"),
    path("cart/", view_cart, name="view_cart"),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", remove_cart_item, name="remove_cart_item"),

    # JWT Auth endpoints
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Payment endpoints
    path("payments/initiate/", initiate_payment, name="initiate_payment"),
    path("payments/verify/<str:tx_ref>/", verify_payment, name="verify_payment"),
    path("payment/success/", payment_success, name="payment_success"),
]
