from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/topup/', views.initiate_topup_view, name='initiate_topup'),
    path('wallet/success/', views.payment_success_view, name='payment_success'),
    path('webhook/razorpay/', views.razorpay_webhook_view, name='razorpay_webhook'),
]
