"""
HotServe — Accounts Models

Custom User model with Requester/Runner roles.
RunnerProfile for verification and trust levels.
Wallet for in-app balance management.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class UserManager(BaseUserManager):
    """Custom manager for User model using email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified_email', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user model for HotServe.
    Every user has one role: REQUESTER, RUNNER, or ADMIN.
    A user can switch between REQUESTER and RUNNER (if verified).
    """

    class Role(models.TextChoices):
        REQUESTER = 'requester', 'Requester'
        RUNNER = 'runner', 'Runner'
        ADMIN = 'admin', 'Admin'

    # ── Core fields ──────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)

    # ── College info ──────────────────────────────────────────────────────
    college_name = models.CharField(max_length=200, blank=True)
    hostel_name = models.CharField(max_length=100, blank=True)
    room_number = models.CharField(max_length=20, blank=True)

    # ── Status flags ──────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified_email = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'hs_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def is_runner(self):
        return self.role == self.Role.RUNNER

    @property
    def is_requester(self):
        return self.role == self.Role.REQUESTER

    @property
    def display_name(self):
        return self.full_name.split()[0] if self.full_name else 'User'

    def update_last_seen(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])


class RunnerProfile(models.Model):
    """
    Extended profile for verified runners.
    Created when a runner application is approved.
    """

    class TrustLevel(models.TextChoices):
        NEW = 'new', '🆕 New Runner'
        TRUSTED = 'trusted', '⭐ Trusted Runner'
        ELITE = 'elite', '🏆 Elite Runner'

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'
        BANNED = 'banned', 'Permanently Banned'

    # ── Link to user ──────────────────────────────────────────────────────
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='runner_profile'
    )

    # ── College verification info ─────────────────────────────────────────
    roll_number = models.CharField(max_length=50, unique=True)
    branch = models.CharField(max_length=100)
    year_of_study = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)]
    )

    # ── Verification documents ────────────────────────────────────────────
    college_portal_screenshot = models.ImageField(upload_to='runner_verification/portal/')
    selfie_with_note = models.ImageField(upload_to='runner_verification/selfies/')
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_runners'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # ── UPI / Bank for payouts ────────────────────────────────────────────
    upi_id = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_ifsc = models.CharField(max_length=15, blank=True)

    # ── Trust level & stats ───────────────────────────────────────────────
    trust_level = models.CharField(
        max_length=20,
        choices=TrustLevel.choices,
        default=TrustLevel.NEW
    )
    total_tasks_completed = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_ratings_count = models.PositiveIntegerField(default=0)

    # ── Complaint / suspension tracking ──────────────────────────────────
    complaint_count = models.PositiveIntegerField(default=0)
    is_online = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)  # Runner can toggle this

    # ── Timestamps ────────────────────────────────────────────────────────
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hs_runner_profiles'
        verbose_name = 'Runner Profile'
        verbose_name_plural = 'Runner Profiles'

    def __str__(self):
        return f"Runner: {self.user.full_name} [{self.trust_level}]"

    @property
    def is_approved(self):
        return self.verification_status == self.VerificationStatus.APPROVED

    @property
    def can_accept_heavy_parcels(self):
        return self.trust_level in [self.TrustLevel.TRUSTED, self.TrustLevel.ELITE]

    def update_trust_level(self):
        """Automatically upgrades trust level based on tasks + rating."""
        elite_tasks = settings.RUNNER_MIN_TASKS_ELITE
        elite_rating = settings.RUNNER_MIN_RATING_ELITE
        trusted_tasks = settings.RUNNER_MIN_TASKS_TRUSTED
        trusted_rating = settings.RUNNER_MIN_RATING_TRUSTED

        if (self.total_tasks_completed >= elite_tasks and
                self.average_rating >= elite_rating):
            self.trust_level = self.TrustLevel.ELITE
        elif (self.total_tasks_completed >= trusted_tasks and
              self.average_rating >= trusted_rating):
            self.trust_level = self.TrustLevel.TRUSTED
        else:
            self.trust_level = self.TrustLevel.NEW
        self.save(update_fields=['trust_level'])

    def update_average_rating(self, new_rating):
        """Incrementally update average rating."""
        total = self.average_rating * self.total_ratings_count + new_rating
        self.total_ratings_count += 1
        self.average_rating = total / self.total_ratings_count
        self.save(update_fields=['average_rating', 'total_ratings_count'])
        self.update_trust_level()

    def add_complaint(self):
        """Increment complaint count and auto-suspend if threshold reached."""
        self.complaint_count += 1
        if self.complaint_count >= settings.AUTO_SUSPEND_COMPLAINT_COUNT:
            self.verification_status = self.VerificationStatus.SUSPENDED
        self.save(update_fields=['complaint_count', 'verification_status'])


class Wallet(models.Model):
    """
    In-app wallet for requesters.
    Balance is held in paise (INR × 100) for accuracy.
    Razorpay top-ups go here. Tasks lock funds in escrow.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    total_topped_up = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hs_wallets'

    def __str__(self):
        return f"Wallet({self.user.display_name}) ₹{self.balance}"

    def can_afford(self, amount):
        return self.balance >= amount

    def deduct(self, amount):
        if not self.can_afford(amount):
            raise ValueError(f"Insufficient balance. Have ₹{self.balance}, need ₹{amount}")
        self.balance -= amount
        self.total_spent += amount
        self.save(update_fields=['balance', 'total_spent'])

    def credit(self, amount):
        self.balance += amount
        self.save(update_fields=['balance'])

    def top_up(self, amount):
        self.balance += amount
        self.total_topped_up += amount
        self.save(update_fields=['balance', 'total_topped_up'])

class OTPCode(models.Model):
    """
    One-Time Password for email verification and password reset.
    Generated as a 6-digit code, expires after OTP_EXPIRY_MINUTES.
    """
 
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Email Verification'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
 
    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
 
    class Meta:
        db_table = 'hs_otp_codes'
        ordering = ['-created_at']
 
    def __str__(self):
        return f"OTP({self.email} — {self.purpose} — {'used' if self.is_used else 'active'})"
 
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
 
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired
 
    @classmethod
    def generate(cls, email, purpose):
        """
        Invalidate any previous OTPs for this email+purpose,
        then create and return a fresh one.
        """
        import random
        # Invalidate old codes
        cls.objects.filter(
            email=email, purpose=purpose, is_used=False
        ).update(is_used=True)
 
        code = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timezone.timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        return cls.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=expires_at
        )
 
    @classmethod
    def verify(cls, email, code, purpose):
        """
        Returns (True, None) if valid, (False, error_message) if not.
        """
        try:
            otp = cls.objects.filter(
                email=email,
                code=code,
                purpose=purpose,
                is_used=False
            ).latest('created_at')
        except cls.DoesNotExist:
            return False, "Invalid OTP code."
 
        if otp.is_expired:
            return False, "OTP has expired. Please request a new one."
 
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return True, None
 