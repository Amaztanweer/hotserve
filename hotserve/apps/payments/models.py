"""
HotServe — Payments Models

EscrowTransaction: Tracks every lock/release/refund for task funds.
WalletTransaction: Full audit trail of wallet credits/debits.
RazorpayOrder: Stores Razorpay payment intent records.
"""

from django.db import models
from django.conf import settings
import uuid


class EscrowTransaction(models.Model):
    """
    Every time money moves in/out of task escrow, it's recorded here.
    LOCK   → requester posts task, funds held
    RELEASE → task confirmed, funds sent to runner
    REFUND  → task cancelled, funds returned to requester
    DISPUTE → admin override
    """

    class Type(models.TextChoices):
        LOCK = 'lock', '🔒 Lock'
        RELEASE = 'release', '✅ Release to Runner'
        REFUND = 'refund', '↩️ Refund to Requester'
        DISPUTE_RELEASE = 'dispute_release', '⚖️ Dispute: Released to Runner'
        DISPUTE_REFUND = 'dispute_refund', '⚖️ Dispute: Refunded to Requester'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.PROTECT,
        related_name='escrow_transactions'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=30, choices=Type.choices)
    description = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_escrows'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hs_escrow_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} ₹{self.amount} [{self.task.task_number}]"


class WalletTransaction(models.Model):
    """Full audit log of every wallet credit and debit."""

    class Type(models.TextChoices):
        TOPUP = 'topup', '💳 Top Up'
        TASK_LOCK = 'task_lock', '🔒 Task Escrow Lock'
        TASK_REFUND = 'task_refund', '↩️ Task Refund'
        RUNNER_EARNING = 'runner_earning', '💰 Runner Earning'
        ADMIN_CREDIT = 'admin_credit', '👮 Admin Credit'
        ADMIN_DEBIT = 'admin_debit', '👮 Admin Debit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet_transactions'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=30, choices=Type.choices)
    is_credit = models.BooleanField()   # True = money in, False = money out
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True)  # Razorpay payment ID etc.
    task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wallet_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hs_wallet_transactions'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.is_credit else '-'
        return f"{sign}₹{self.amount} | {self.user.display_name} | {self.transaction_type}"


class RazorpayOrder(models.Model):
    """
    Tracks Razorpay payment orders for wallet top-ups.
    Created before payment, updated after webhook confirmation.
    """

    class Status(models.TextChoices):
        CREATED = 'created', 'Created'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='razorpay_orders'
    )
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # INR
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'hs_razorpay_orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Razorpay {self.razorpay_order_id} ₹{self.amount} [{self.status}]"
