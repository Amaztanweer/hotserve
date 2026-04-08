from django.urls import path
from . import api_views

app_name = 'api_payments'

urlpatterns = [
    path('create-order/', api_views.CreateRazorpayOrderAPIView.as_view(), name='create_order'),
    path('confirm/', api_views.ConfirmPaymentAPIView.as_view(), name='confirm'),
    path('transactions/', api_views.WalletTransactionListAPIView.as_view(), name='transactions'),
]
