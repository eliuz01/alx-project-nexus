from rest_framework import viewsets, status
from .models import Category, Product, Order, User, Payment, CartItem, Cart, OrderItem
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

    def perform_create(self, serializer):
        user = self.request.user
        cart = Cart.objects.filter(user=user).first()

        if not cart or not cart.items.exists():
            raise ValidationError({"error": "Cart is empty"})

        # Create the order
        order = serializer.save(user=user, status="PENDING", total_price=0)

        total_price = 0
        for item in cart.items.all():
            subtotal = item.product.price * item.quantity
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            total_price += subtotal

        # Update total price
        order.total_price = total_price
        order.save()

        # Clear the cart
        cart.items.all().delete()   

        
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

@swagger_auto_schema(
    method="get",
    responses={200: CartSerializer}
)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_cart(request):
    cart = get_user_cart(request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@swagger_auto_schema(
    method="post",
    request_body=CartItemSerializer,
    responses={201: CartItemSerializer}
)

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


@swagger_auto_schema(
    method="patch",
    request_body=CartItemSerializer,
    responses={200: CartItemSerializer, 400: "Bad Request", 404: "Item not found"}
)
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

@swagger_auto_schema(
    method="delete",
    responses={200: "Item removed", 404: "Item not found"}
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_cart_item(request, item_id):
    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
        item.delete()
        return Response({"message": "Item removed"})
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found"}, status=404)
    

@swagger_auto_schema(
    method="post",
    request_body=None,
    responses={201: OrderSerializer, 400: "Cart is empty"}
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])  
def create_order_from_cart(request):
    # 1. Get the user’s cart
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return Response({"error": "Cart is empty"}, status=400)

    # 2. Create the order
    order = Order.objects.create(
        user=request.user,
        total_price=sum(item.subtotal for item in cart.items.all())
    )

    # 3. Move cart items into order
    for item in cart.items.all():
        subtotal = item.product.price * item.quantity
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price 
        )
        total_price += subtotal

    # 4. Update total
    order.total_price = total_price
    order.save()

    #Clear the cart
    cart.items.all().delete()

    #Return response
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=201)


@swagger_auto_schema(
    method="post",
    operation_description="Checkout: Convert cart items into an order and initiate payment.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "payment_method": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Payment method (default: chapa)",
                example="chapa"
            ),
        },
        required=[],
    ),
    responses={
        201: openapi.Response(
            description="Order created and payment initiated",
            examples={
                "application/json": {
                    "order": {
                        "id": 5,
                        "user": 3,
                        "total_price": 2500,
                        "status": "pending",
                        "items": [
                            {"id": 1, "product": "AA Big Book", "quantity": 1, "subtotal": 1000},
                            {"id": 2, "product": "AA Magazine", "quantity": 2, "subtotal": 1500}
                        ]
                    },
                    "payment": {
                        "id": 12,
                        "tx_ref": "5eaf3b8d-32c7-4b0e-8dd7-5b8ff8a0c61d",
                        "amount": "2500.00",
                        "currency": "ETB",
                        "status": "pending"
                    },
                    "chapa_response": {
                        "status": "success",
                        "data": {
                            "checkout_url": "https://chapa.link/pay/xxxxxxx"
                        }
                    }
                }
            }
        ),
        400: "Cart is empty"
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    user = request.user
    cart = user.cart  # since you use get_or_create, you can also call get_user_cart(user)

    if not cart.items.exists():
        return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

    # Step 1: Create Order
    order = Order.objects.create(user=user, status="pending", total_price=0)

    total_price = 0
    for item in cart.items.all():
        subtotal = item.product.price * item.quantity
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity
        )
        total_price += subtotal

    order.total_price = total_price
    order.save()

    # Step 2: Clear cart
    cart.items.all().delete()

    # Step 3: Create Payment record
    tx_ref = str(uuid.uuid4())
    payment = Payment.objects.create(
        order=order,
        tx_ref=tx_ref,
        amount=total_price,
        currency="ETB",
        status="pending",
    )

    # Step 4: Call Chapa initialize API
    payload = {
        "amount": str(total_price),
        "currency": "ETB",
        "email": user.email,
        "first_name": user.username,
        "last_name": "Customer",
        "tx_ref": tx_ref,
        "callback_url": "http://127.0.0.1:8000/api/payments/verify/",
        "return_url": "http://127.0.0.1:8000/payment/success/",
    }

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(f"{settings.CHAPA_BASE_URL}/transaction/initialize",
                             json=payload, headers=headers)
    chapa_data = response.json()

    return Response({
        "order": OrderSerializer(order).data,
        "payment": PaymentSerializer(payment).data,
        "chapa_response": chapa_data
    }, status=status.HTTP_201_CREATED)