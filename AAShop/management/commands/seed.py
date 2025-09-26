from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from AAShop.models import Category, Product

User = get_user_model()

class Command(BaseCommand):
    help = "Seed database with initial data"

    def handle(self, *args, **kwargs):
        # Create superuser if not exists
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@gmail.com", "admin123")
            self.stdout.write(self.style.SUCCESS("Superuser created: admin / admin123"))
        else:
            self.stdout.write("Superuser already exists")

        # Seed Categories
        categories = ["Books", "Meditation", "Merchandise"]
        for name in categories:
            Category.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Categories seeded"))

        # Seed Products
        products = [
            {"name": "AA Big Book", "description": "Basic Text for Alcoholics Anonymous", "price": 1000, "stock": 50, "category": "Books"},
            {"name": "Daily Reflections", "description": "Inspirational AA Reflections", "price": 800, "stock": 30, "category": "Books"},
            {"name": "AA Mug", "description": "AA Branded Coffee Mug", "price": 500, "stock": 20, "category": "Merchandise"},
        ]

        for prod in products:
            category = Category.objects.get(name=prod["category"])
            Product.objects.get_or_create(
                name=prod["name"],
                defaults={
                    "description": prod["description"],
                    "price": prod["price"],
                    "stock": prod["stock"],
                    "category": category
                }
            )
        self.stdout.write(self.style.SUCCESS("Products seeded"))
