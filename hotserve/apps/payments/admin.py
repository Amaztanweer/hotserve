from django.contrib import admin
from .models import EscrowTransaction, WalletTransaction, RazorpayOrder


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = ['task', 'transaction_type', 'amount', 'created_at']
    list_filter = ['transaction_type']
    readonly_fields = ['id', 'created_at']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'is_credit', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'is_credit']
    search_fields = ['user__email', 'reference_id']
    readonly_fields = ['id', 'created_at']


@admin.register(RazorpayOrder)
class RazorpayOrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'razorpay_order_id', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['id', 'created_at', 'paid_at']
