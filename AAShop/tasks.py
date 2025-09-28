from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_payment_confirmation_email(user_email, order_id, amount, status):
    subject = "Payment Confirmation"
    message = f"Your payment for Order #{order_id} of {amount} ETB has been marked as {status}."
    send_mail(subject, message, "no-reply@yourshop.com", [user_email])
