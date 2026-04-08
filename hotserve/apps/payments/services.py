"""
HotServe — Payments Service Layer

All payment business logic lives here.
Views and signals call these functions; never put payment logic in models.
"""

from django.conf import settings
from django.db import transaction
from django.utils import timezone
import razorpay
import hmac
import hashlib

from .models import EscrowTransaction, WalletTransaction, RazorpayOrder


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ─────────────────────────────────────────────────────────────────────────────
# ESCROW
# ─────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def release_escrow_to_runner(task):
    """
    Called when requester confirms delivery.
    Releases runner_payout to runner's wallet.
    Platform keeps platform_fee.
    """
    from apps.accounts.models import RunnerProfile

    runner = task.runner
    runner_wallet = runner.wallet

    # Credit runner
    runner_wallet.credit(task.runner_payout)

    # Record escrow release
    EscrowTransaction.objects.create(
        task=task,
        amount=task.runner_payout,
        transaction_type=EscrowTransaction.Type.RELEASE,
        description=f"Escrow released to runner for task {task.task_number}"
    )

    # Record wallet transaction for runner
    WalletTransaction.objects.create(
        user=runner,
        amount=task.runner_payout,
        transaction_type=WalletTransaction.Type.RUNNER_EARNING,
        is_credit=True,
        balance_after=runner_wallet.balance,
        task=task,
        description=f"Earning from task {task.task_number}"
    )

    # Update runner stats
    try:
        rp = RunnerProfile.objects.get(user=runner)
        rp.total_tasks_completed += 1
        rp.total_earnings += task.runner_payout
        rp.save(update_fields=['total_tasks_completed', 'total_earnings'])
        rp.update_trust_level()
    except RunnerProfile.DoesNotExist:
        pass


@transaction.atomic
def refund_escrow_to_requester(task, processed_by=None, transaction_type=EscrowTransaction.Type.REFUND):
    """
    Refund locked escrow back to requester.
    Used on cancellation or admin dispute resolution.
    """
    requester = task.requester
    wallet = requester.wallet
    amount = task.total_locked_amount

    wallet.credit(amount)

    EscrowTransaction.objects.create(
        task=task,
        amount=amount,
        transaction_type=transaction_type,
        description=f"Refund for task {task.task_number}",
        processed_by=processed_by
    )

    WalletTransaction.objects.create(
        user=requester,
        amount=amount,
        transaction_type=WalletTransaction.Type.TASK_REFUND,
        is_credit=True,
        balance_after=wallet.balance,
        task=task,
        description=f"Refund for cancelled task {task.task_number}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# WALLET TOP-UP VIA RAZORPAY
# ─────────────────────────────────────────────────────────────────────────────

def create_razorpay_order(user, amount_inr):
    """
    Creates a Razorpay order for wallet top-up.
    Returns (razorpay_order, db_order).
    """
    client = get_razorpay_client()
    amount_paise = int(amount_inr * 100)  # Razorpay uses paise

    rz_order = client.order.create({
        'amount': amount_paise,
        'currency': settings.RAZORPAY_CURRENCY,
        'payment_capture': 1,
        'notes': {
            'user_id': str(user.id),
            'user_email': user.email,
            'purpose': 'HotServe wallet top-up'
        }
    })

    db_order = RazorpayOrder.objects.create(
        user=user,
        razorpay_order_id=rz_order['id'],
        amount=amount_inr
    )

    return rz_order, db_order


@transaction.atomic
def confirm_razorpay_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Called from Razorpay webhook or payment success callback.
    Verifies signature, credits wallet, marks order as paid.
    """
    try:
        db_order = RazorpayOrder.objects.select_for_update().get(
            razorpay_order_id=razorpay_order_id,
            status=RazorpayOrder.Status.CREATED
        )
    except RazorpayOrder.DoesNotExist:
        return False, "Order not found or already processed."

    # Verify Razorpay signature
    key_secret = settings.RAZORPAY_KEY_SECRET.encode()
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        db_order.status = RazorpayOrder.Status.FAILED
        db_order.save()
        return False, "Signature verification failed."

    # Credit wallet
    user = db_order.user
    wallet = user.wallet
    wallet.top_up(db_order.amount)

    # Record wallet transaction
    WalletTransaction.objects.create(
        user=user,
        amount=db_order.amount,
        transaction_type=WalletTransaction.Type.TOPUP,
        is_credit=True,
        balance_after=wallet.balance,
        reference_id=razorpay_payment_id,
        description=f"Wallet top-up via Razorpay"
    )

    # Update order record
    db_order.razorpay_payment_id = razorpay_payment_id
    db_order.razorpay_signature = razorpay_signature
    db_order.status = RazorpayOrder.Status.PAID
    db_order.paid_at = timezone.now()
    db_order.save()

    return True, f"₹{db_order.amount} credited to wallet."
