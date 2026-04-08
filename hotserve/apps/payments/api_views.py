"""
HotServe — Payments API Views
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status, serializers
from django.conf import settings
from .models import WalletTransaction
from .services import create_razorpay_order, confirm_razorpay_payment


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'amount', 'transaction_type', 'is_credit',
            'balance_after', 'description', 'created_at'
        ]


class WalletTransactionListAPIView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer

    def get_queryset(self):
        return WalletTransaction.objects.filter(user=self.request.user)


class CreateRazorpayOrderAPIView(APIView):
    def post(self, request):
        amount = request.data.get('amount')
        try:
            amount = float(amount)
            if amount < settings.WALLET_MIN_TOPUP:
                return Response(
                    {'error': f'Minimum top-up is ₹{settings.WALLET_MIN_TOPUP}'},
                    status=400
                )
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount'}, status=400)

        rz_order, db_order = create_razorpay_order(request.user, amount)
        return Response({
            'order_id': rz_order['id'],
            'amount': amount,
            'currency': 'INR',
            'razorpay_key': settings.RAZORPAY_KEY_ID,
        })


class ConfirmPaymentAPIView(APIView):
    def post(self, request):
        order_id = request.data.get('razorpay_order_id')
        payment_id = request.data.get('razorpay_payment_id')
        signature = request.data.get('razorpay_signature')

        success, message = confirm_razorpay_payment(order_id, payment_id, signature)
        if success:
            return Response({'message': message})
        return Response({'error': message}, status=400)
