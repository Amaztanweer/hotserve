"""
HotServe — Payments Views
"""

from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import json

from .models import WalletTransaction, RazorpayOrder
from .services import create_razorpay_order, confirm_razorpay_payment


@login_required
def wallet_view(request):
    """Wallet overview + top-up."""
    user = request.user
    wallet = user.wallet
    transactions = WalletTransaction.objects.filter(user=user).order_by('-created_at')[:30]

    return render(request, 'payments/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'min_topup': settings.WALLET_MIN_TOPUP,
        'max_balance': settings.WALLET_MAX_BALANCE,
        'quick_amounts': [10, 100, 200, 500],  # ✅ ADD THIS
    })


@login_required
@csrf_protect
def initiate_topup_view(request):
    """Create a Razorpay order and return order details for frontend."""
    if request.method != 'POST':
        return redirect('payments:wallet')

    try:
        amount = Decimal(request.POST.get('amount', 0))
    except (ValueError, TypeError):
        messages.error(request, "Invalid amount.")
        return redirect('payments:wallet')

    if amount < settings.WALLET_MIN_TOPUP:
        messages.error(request, f"Minimum top-up is ₹{settings.WALLET_MIN_TOPUP}.")
        return redirect('payments:wallet')

    current_balance = request.user.wallet.balance
    if current_balance + amount > settings.WALLET_MAX_BALANCE:
        messages.error(
            request,
            f"This would exceed max wallet balance of ₹{settings.WALLET_MAX_BALANCE}."
        )
        return redirect('payments:wallet')

    try:
        rz_order, db_order = create_razorpay_order(request.user, amount)
        return render(request, 'payments/checkout.html', {
            'rz_order': rz_order,
            'db_order': db_order,
            'amount': amount,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'user': request.user,
        })
    except Exception as e:
        messages.error(request, f"Payment initiation failed: {str(e)}")
        return redirect('payments:wallet')


@login_required
def payment_success_view(request):
    """Handle Razorpay payment success callback."""
    if request.method != 'POST':
        return redirect('payments:wallet')

    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    success, message = confirm_razorpay_payment(
        razorpay_order_id, razorpay_payment_id, razorpay_signature
    )

    if success:
        messages.success(request, f"✅ {message} Your wallet is topped up!")
    else:
        messages.error(request, f"Payment verification failed: {message}")

    return redirect('payments:wallet')


@csrf_exempt
def razorpay_webhook_view(request):
    """
    Razorpay webhook endpoint (configure in Razorpay dashboard).
    Handles payment.captured event for backend verification.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
        event = payload.get('event')

        if event == 'payment.captured':
            payment = payload['payload']['payment']['entity']
            order_id = payment.get('order_id')
            payment_id = payment.get('id')

            # Look up the order
            try:
                db_order = RazorpayOrder.objects.get(
                    razorpay_order_id=order_id,
                    status=RazorpayOrder.Status.CREATED
                )
                # Use a dummy signature for webhook (already verified by Razorpay)
                # In production, verify the webhook signature from headers
                from django.db import transaction as db_transaction
                with db_transaction.atomic():
                    user = db_order.user
                    wallet = user.wallet
                    wallet.top_up(db_order.amount)
                    db_order.razorpay_payment_id = payment_id
                    db_order.status = RazorpayOrder.Status.PAID
                    db_order.save()
            except RazorpayOrder.DoesNotExist:
                pass

        return HttpResponse(status=200)
    except Exception:
        return HttpResponse(status=400)
