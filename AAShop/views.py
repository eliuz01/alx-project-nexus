from rest_framework import viewsets
from .models import Category, Product, Order, User, Payment
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer, UserSerializer, PaymentSerializer, PaymentInitiateRequestSerializer
import requests
import uuid
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


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

    payment = Payment.objects.create(
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
            payment.transaction_id = data["data"].get("reference")  # use reference instead of id
        else:
            payment.status = "failed"
        payment.save()
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)

    return Response({"chapa_response": data, "payment": PaymentSerializer(payment).data})