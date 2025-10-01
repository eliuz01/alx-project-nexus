### AAkenyaShop – Project Documentation
## 1. Introduction

AAKenyaShop is an e-commerce backend built with Django REST Framework (DRF). The project allows users to register, browse products, manage shopping carts, place orders, and process payments using the Chapa payment gateway.

The goal is to provide a robust API backend that can be consumed by web or mobile applications for a full online shopping experience.

## 2. Key Features

User Authentication & Registration

JWT authentication (via DRF SimpleJWT).

Signup requires email, first name, last name, password, and phone number.

Product Management

Categories and products with seed data.

Autoload products via seeder for demo purposes.

Cart System

Add items to cart.

Update or remove cart items.

View current cart contents.

Order Management

Place orders from the cart.

Order status tracking.

Payment Integration (Chapa)

Initiate payment via Chapa API.

Verify payment callback.

Redirect to payment/success/ page on successful transactions.

## 3. Tech Stack

Backend Framework: Django 5 + Django REST Framework

Authentication: JWT (via djangorestframework-simplejwt)

Database: PostgreSQL / MySQL (configurable)

Payment Gateway: Chapa
 API

Deployment: PythonAnywhere / local dev environment


## 4. API Endpoints
Endpoint	Method	Description
/api/register/	POST	Register user
/api/token/	POST	Get JWT token
/categories/	GET	List categories
/products/	GET	List products
/cart/	GET	View user cart
/cart/add/	POST	Add item to cart
/cart/update/<id>/	PUT	Update cart item
/cart/remove/<id>/	DELETE	Remove cart item
/orders/	GET/POST	List or create orders
/payments/initiate/	POST	Start Chapa payment
/payments/verify/<tx_ref>/	GET	Verify Chapa payment
/payment/success/	GET	Success redirect page
## 5. Payment Flow (Chapa)

Initiate Payment

User places order.

Backend sends payment request to Chapa with:

amount, currency, tx_ref, email, first_name, last_name, phone, return_url, callback_url.

Chapa returns checkout_url.

User Redirected

User completes payment on Chapa’s hosted checkout.

Chapa Callback

Chapa calls callback_url → /api/payments/verify/<tx_ref>/.

Backend verifies and updates order status to paid.

Success Page

User is redirected to /payment/success/.

## 6. Testing

Run tests:

python manage.py test


Example login request:

POST /api/register/
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+254712345678",
  "password": "john12"
}

## 7. Future Enhancements

Add shipping and delivery tracking.

Implement product reviews & ratings.

Add mobile money integrations (e.g., M-Pesa).

Deploy frontend (React/Vue) consuming this API.