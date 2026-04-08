"""
Auto-create a Wallet whenever a new User is created.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Wallet


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Every new user gets a wallet automatically."""
    if created:
        Wallet.objects.get_or_create(user=instance)
