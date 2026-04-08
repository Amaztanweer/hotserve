"""
HotServe — Tasks Models

Task: Core model representing a delivery/errand request.
TaskCategory: Food, Stationery, Parcels, Laundry, etc.
TaskBid: Runner expresses interest in a task.
Rating: Post-completion review.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class TaskCategory(models.Model):
    """
    Configurable task categories set up by admin.
    Each category has base reward and trust requirements.
    """

    class TrustRequirement(models.TextChoices):
        ALL = 'new', 'All Runners'
        TRUSTED = 'trusted', 'Trusted + Elite Only'
        ELITE = 'elite', 'Elite Only'

    name = models.CharField(max_length=80, unique=True)
    icon = models.CharField(max_length=10, default='📦')    # Emoji icon
    description = models.CharField(max_length=200, blank=True)
    base_reward_min = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    base_reward_max = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    min_trust_required = models.CharField(
        max_length=20,
        choices=TrustRequirement.choices,
        default=TrustRequirement.ALL
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'hs_task_categories'
        ordering = ['sort_order', 'name']
        verbose_name = 'Task Category'
        verbose_name_plural = 'Task Categories'

    def __str__(self):
        return f"{self.icon} {self.name}"


class Task(models.Model):
    """
    The central model. A requester posts a task;
    a runner picks it up and completes it.
    """

    class Status(models.TextChoices):
        OPEN = 'open', '🟢 Open'                        # Waiting for runner
        ACCEPTED = 'accepted', '🔵 Accepted'             # Runner picked it
        PICKED_UP = 'picked_up', '🟠 Picked Up'          # Runner has item
        DELIVERED = 'delivered', '🟡 Delivered'          # Runner says done
        CONFIRMED = 'confirmed', '✅ Confirmed'          # Requester confirmed, escrow released
        CANCELLED = 'cancelled', '❌ Cancelled'          # By requester or expired
        DISPUTED = 'disputed', '⚠️ Disputed'            # Admin needs to step in

    class DeliveryType(models.TextChoices):
        STANDARD = 'standard', 'Standard Delivery'
        URGENT = 'urgent', 'Urgent (2x reward)'

    # ── Identity ──────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_number = models.CharField(max_length=12, unique=True, editable=False)

    # ── Participants ──────────────────────────────────────────────────────
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='posted_tasks'
    )
    runner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accepted_tasks'
    )

    # ── Task details ──────────────────────────────────────────────────────
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.PROTECT,
        related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
        default=DeliveryType.STANDARD
    )

    # ── Location ──────────────────────────────────────────────────────────
    pickup_location = models.CharField(max_length=200)    # e.g. "Canteen Block B"
    delivery_location = models.CharField(max_length=200)  # e.g. "Block A Room 204"

    # ── Financials (stored in INR) ─────────────────────────────────────────
    reward_amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(5)]
    )
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    runner_payout = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # ── Pre-purchase tasks ────────────────────────────────────────────────
    requires_purchase = models.BooleanField(default=False)
    purchase_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # ── Status & lifecycle ────────────────────────────────────────────────
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    is_escrow_locked = models.BooleanField(default=False)  # Money locked in platform

    # ── Images (optional proof) ───────────────────────────────────────────
    task_image = models.ImageField(upload_to='task_images/', null=True, blank=True)
    delivery_proof_image = models.ImageField(upload_to='delivery_proof/', null=True, blank=True)

    # ── Cancellation ──────────────────────────────────────────────────────
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cancelled_tasks'
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Auto-cancel if unaccepted

    class Meta:
        db_table = 'hs_tasks'
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return f"[{self.task_number}] {self.title} — {self.status}"

    def save(self, *args, **kwargs):
        # Auto-generate task number on first save
        if not self.task_number:
            self.task_number = self._generate_task_number()
        # Calculate platform fee and runner payout
        if self.reward_amount and not self.platform_fee:
            pct = settings.PLATFORM_COMMISSION_PERCENT
            self.platform_fee = round(self.reward_amount * pct / 100, 2)
            self.runner_payout = self.reward_amount - self.platform_fee
        super().save(*args, **kwargs)

    def _generate_task_number(self):
        import random, string
        chars = string.ascii_uppercase + string.digits
        return 'HS' + ''.join(random.choices(chars, k=8))

    @property
    def total_locked_amount(self):
        """Total amount locked in escrow = reward + purchase if applicable."""
        return self.reward_amount + (self.purchase_amount if self.requires_purchase else 0)

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

    @property
    def is_active(self):
        return self.status in [self.Status.ACCEPTED, self.Status.PICKED_UP]

    @property
    def is_completed(self):
        return self.status == self.Status.CONFIRMED

    def accept(self, runner):
        """Runner accepts the task."""
        self.runner = runner
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save(update_fields=['runner', 'status', 'accepted_at'])

    def mark_picked_up(self):
        self.status = self.Status.PICKED_UP
        self.picked_up_at = timezone.now()
        self.save(update_fields=['status', 'picked_up_at'])

    def mark_delivered(self):
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])

    def confirm(self):
        """Requester confirms delivery. Triggers escrow release."""
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_at'])

    def cancel(self, cancelled_by_user, reason=''):
        self.status = self.Status.CANCELLED
        self.cancelled_by = cancelled_by_user
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_by', 'cancellation_reason'])

    def raise_dispute(self):
        self.status = self.Status.DISPUTED
        self.save(update_fields=['status'])


class Rating(models.Model):
    """
    Post-completion rating from requester → runner.
    One rating per task, 1-5 stars + optional comment.
    """

    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='rating')
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_ratings'
    )
    runner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_ratings'
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hs_ratings'

    def __str__(self):
        return f"Rating for {self.task.task_number}: {self.stars}⭐"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update runner's average rating in RunnerProfile
        from apps.accounts.models import RunnerProfile
        try:
            rp = RunnerProfile.objects.get(user=self.runner)
            rp.update_average_rating(self.stars)
        except RunnerProfile.DoesNotExist:
            pass
