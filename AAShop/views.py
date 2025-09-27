from rest_framework import viewsets
from .models import Category, Product, Order, User, Payment
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer, UserSerializer, PaymentSerializer
import requests
import uuid
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    amount = request.data.get("amount")
    currency = request.data.get("currency", "ETB")
    email = request.data.get("email", "test@example.com")
    first_name = request.data.get("first_name", "John")
    last_name = request.data.get("last_name", "Doe")

    tx_ref = str(uuid.uuid4())  # generate unique reference

    payload = {
        "amount": amount,
        "currency": currency,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
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

    data = response.json()

    # save payment record
    payment = Payment.objects.create(
        tx_ref=tx_ref,
        amount=amount,
        currency=currency,
        status="pending",
    )

    return Response({"chapa_response": data, "payment": PaymentSerializer(payment).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_payment(request, tx_ref):
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
    }

    response = requests.get(
        f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}",
        headers=headers,
    )

    data = response.json()

    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
        if data.get("status") == "success":
            payment.status = "completed"
            payment.transaction_id = data["data"]["id"]
        else:
            payment.status = "failed"
        payment.save()
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)

    return Response({"chapa_response": data, "payment": PaymentSerializer(payment).data})
