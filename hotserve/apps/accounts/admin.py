from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RunnerProfile, Wallet


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'is_active', 'is_verified_email', 'created_at']
    list_filter = ['role', 'is_active', 'is_verified_email']
    search_fields = ['email', 'full_name', 'hostel_name']
    ordering = ['-created_at']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('full_name', 'phone', 'profile_photo')}),
        ('College', {'fields': ('college_name', 'hostel_name', 'room_number')}),
        ('Role & Status', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified_email')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(RunnerProfile)
class RunnerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'roll_number', 'branch', 'verification_status',
        'trust_level', 'total_tasks_completed', 'average_rating'
    ]
    list_filter = ['verification_status', 'trust_level', 'year_of_study']
    search_fields = ['user__email', 'user__full_name', 'roll_number']
    readonly_fields = ['applied_at', 'verified_at', 'total_tasks_completed', 'average_rating']
    actions = ['approve_runners', 'reject_runners', 'ban_runners']

    def approve_runners(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            verification_status='approved',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f"{queryset.count()} runners approved.")
    approve_runners.short_description = "✅ Approve selected runners"

    def ban_runners(self, request, queryset):
        queryset.update(verification_status='banned')
        self.message_user(request, f"{queryset.count()} runners banned.")
    ban_runners.short_description = "🚫 Ban selected runners"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'total_topped_up', 'total_spent']
    search_fields = ['user__email', 'user__full_name']
    readonly_fields = ['total_topped_up', 'total_spent']
