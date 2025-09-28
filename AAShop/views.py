from rest_framework import viewsets, status
from .models import Category, Product, Order, User, Payment, CartItem, Cart
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer, UserSerializer, PaymentSerializer, PaymentInitiateRequestSerializer, RegisterSerializer, CartItemSerializer, CartSerializer
import requests, uuid

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .tasks import send_payment_confirmation_email


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

@swagger_auto_schema(
    method="post",
    request_body=PaymentInitiateRequestSerializer,
    responses={200: PaymentSerializer}
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    serializer = PaymentInitiateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    tx_ref = str(uuid.uuid4())

    payload = {
        "amount": str(data["amount"]), 
        "currency": data["currency"],
        "email": data["email"],
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "tx_ref": tx_ref,
        "callback_url": "http://127.0.0.1:8000/api/payments/verify/",
        "return_url": "http://127.0.0.1:8000/payment/success/",
    }

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{settings.CHAPA_BASE_URL}/transaction/initialize",
        json=payload,
        headers=headers,
    )

    chapa_data = response.json()
    
    
    order = Order.objects.get(id=data["order_id"])
    payment = Payment.objects.create(
        order=order,
        tx_ref=tx_ref,
        amount=data["amount"],
        currency=data["currency"],
        status="pending",
    )

    return Response(
        {"chapa_response": chapa_data, "payment": PaymentSerializer(payment).data}
    )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "tx_ref",
            openapi.IN_PATH,
            description="Transaction reference to verify",
            type=openapi.TYPE_STRING,
            required=True,
        )
    ],
    responses={200: PaymentSerializer}
)
@api_view(["GET"]) 
@permission_classes([IsAuthenticated])
def verify_payment(request, tx_ref):
    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}

    response = requests.get(
        f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}",
        headers=headers,
    )
    data = response.json()

    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
        if data.get("status") == "success" and data["data"].get("status") == "success":
            payment.status = "completed"
            payment.transaction_id = data["data"].get("reference") 

            #trigger Celery task here
            from .tasks import send_payment_confirmation_email
            send_payment_confirmation_email.delay(
                request.user.email, payment.order.id, str(payment.amount), payment.status
            )
        else:
            payment.status = "failed"
        payment.save()
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)

    return Response({"chapa_response": data, "payment": PaymentSerializer(payment).data})


@api_view(["POST"])
@permission_classes([])  # open endpoint, secured by signature later
def chapa_webhook(request):
    data = request.data
    tx_ref = data.get("tx_ref")
    status = data.get("status")

    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
        if status == "success":
            payment.status = "completed"
            payment.transaction_id = data.get("reference")
            payment.save()
            send_payment_confirmation_email.delay(
                payment.order.user.email, payment.order.id, str(payment.amount), payment.status
            )
    except Payment.DoesNotExist:
        pass

    return Response({"message": "Webhook processed"}, status=200)


@swagger_auto_schema(
    method="post",
    request_body=RegisterSerializer,
    responses={201: openapi.Response("User registered successfully")}
)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {"message": "User registered successfully!"},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_user_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart = get_user_cart(request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    cart = get_user_cart(request.user)
    serializer = CartItemSerializer(data=request.data)
    if serializer.is_valid():
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity
        item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found"}, status=404)

    serializer = CartItemSerializer(item, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_cart_item(request, item_id):
    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
        item.delete()
        return Response({"message": "Item removed"})
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found"}, status=404)
    