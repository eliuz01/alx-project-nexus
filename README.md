# ProDev Backend Engineering Program

## Overview

This repository contains my final project for the **ALX ProDev Backend Engineering Program**. The journey through this program has been both challenging and rewarding, equipping me with the skills and mindset needed to build reliable, scalable backend systems.

## Major Learnings

### Key Technologies

* **Python** – My primary tool for backend logic and problem solving
* **Django** – Framework I used to build structured, production-ready APIs
* **REST APIs & GraphQL** – Designing endpoints that are both flexible and efficient
* **Docker** – Simplifying development and deployment across environments
* **CI/CD** – Setting up pipelines for continuous testing and delivery

### Core Concepts

* **Database Design** – Creating schemas that balance performance and integrity
* **Asynchronous Programming** – Improving responsiveness with async tasks
* **Caching Strategies** – Reducing database load and speeding up requests

### Challenges & Solutions

* Tackling slow queries → I learned to optimize ORM queries and indexes
* Handling environment configurations → Adopted `django-environ` and containerized secrets
* Scaling APIs → Used caching layers and Celery task queues for efficiency

### Best Practices & Personal Takeaways

* Write clean, modular, and test-driven code
* Always document APIs for ease of use and collaboration
* Security and scalability must be built in from the start
* Continuous learning and adaptability are as important as technical skills

## Models Overview 
### User

A custom user model based on AbstractUser.
Uses email as the login field instead of just username.
Can log in, authenticate via JWT, and place orders.

### Category

Groups products logically.
Example: Electronics, Books, Fashion.
Each category can have multiple products.

### Product

Belongs to a Category.
Stores product details: name, description, price, stock.
Example:
Category: Electronics
Product: Samsung Galaxy S22, $699, 10 in stock

### Order

Represents a checkout event.
Belongs to a User.
Has a status (Pending, Paid, Shipped, Cancelled).
Stores total_price (sum of all OrderItems).
Automatically tracks timestamps (created_at, updated_at).

### OrderItem

Represents one product line inside an Order.
Stores:
product (e.g., Samsung Galaxy S22)
quantity (e.g., 2 units)
price (snapshot of product price at the time of order → prevents price changes from affecting old orders).

## Ordering Flow

### Step 1 – User Browses Products
Customer fetches products via API (GET /products/).
Products can be filtered by category, sorted by price, or paginated.

### Step 2 – User Adds Products to Cart

When the customer clicks “Add to Cart”:
A new Order is created with status=PENDING (if none exists).
An OrderItem is added linking that product with quantity.
Example:

Order #101 (Pending, User: eliuz@example.com
)
1 × Samsung Galaxy S22 @ $699

2 × Wireless Charger @ $29

### Step 3 – Checkout

When the customer checks out:
System calculates total_price = sum(order.items.price × quantity).
Order status remains PENDING until payment is confirmed.

### Step 4 – Payment

After successful payment:
Order status = PAID.
Stock is reduced for each product purchased.

### Step 5 – Shipping

Admin or system updates status:
SHIPPED when dispatched.
CANCELLED if customer cancels or payment fails.