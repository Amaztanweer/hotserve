"""
HotServe — Admin Panel Views

Only accessible to users with is_staff=True.
Handles runner approvals, dispute resolution, bans, and live dashboard.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from apps.accounts.models import User, RunnerProfile, Wallet
from apps.tasks.models import Task, TaskCategory, Rating
from apps.payments.models import EscrowTransaction, WalletTransaction, RazorpayOrder
from apps.chat.models import ChatRoom, Message
from apps.payments.services import release_escrow_to_runner, refund_escrow_to_requester


def staff_required(view_func):
    """Decorator: only allow staff/admin users."""
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url='/accounts/login/'
    )(view_func)


@staff_required
def dashboard_view(request):
    """Main admin dashboard with live stats."""
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── User stats ────────────────────────────────────────────────────────
    total_users = User.objects.filter(is_staff=False).count()
    new_users_week = User.objects.filter(created_at__gte=week_ago, is_staff=False).count()

    # ── Runner stats ──────────────────────────────────────────────────────
    total_runners = RunnerProfile.objects.filter(
        verification_status=RunnerProfile.VerificationStatus.APPROVED
    ).count()
    pending_approvals = RunnerProfile.objects.filter(
        verification_status=RunnerProfile.VerificationStatus.PENDING
    ).count()
    online_runners = RunnerProfile.objects.filter(is_online=True).count()

    # ── Task stats ────────────────────────────────────────────────────────
    total_tasks = Task.objects.count()
    active_tasks = Task.objects.filter(
        status__in=[Task.Status.OPEN, Task.Status.ACCEPTED, Task.Status.PICKED_UP]
    ).count()
    completed_today = Task.objects.filter(
        status=Task.Status.CONFIRMED,
        confirmed_at__date=today
    ).count()
    disputed_tasks = Task.objects.filter(status=Task.Status.DISPUTED).count()

    # ── Financial stats ───────────────────────────────────────────────────
    total_processed = Task.objects.filter(
        status=Task.Status.CONFIRMED
    ).aggregate(total=Sum('reward_amount'))['total'] or 0

    platform_revenue = Task.objects.filter(
        status=Task.Status.CONFIRMED
    ).aggregate(total=Sum('platform_fee'))['total'] or 0

    week_revenue = Task.objects.filter(
        status=Task.Status.CONFIRMED,
        confirmed_at__gte=week_ago
    ).aggregate(total=Sum('platform_fee'))['total'] or 0

    # ── Recent activity ───────────────────────────────────────────────────
    recent_tasks = Task.objects.select_related(
        'requester', 'runner', 'category'
    ).order_by('-created_at')[:10]

    recent_signups = User.objects.filter(
        is_staff=False
    ).order_by('-created_at')[:5]

    # ── Top runners ───────────────────────────────────────────────────────
    top_runners = RunnerProfile.objects.filter(
        verification_status=RunnerProfile.VerificationStatus.APPROVED
    ).select_related('user').order_by('-total_tasks_completed')[:5]

    # ── Daily task chart (last 7 days) ────────────────────────────────────
    daily_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Task.objects.filter(created_at__date=day).count()
        daily_data.append({'date': day.strftime('%a'), 'count': count})

    context = {
        'stats': {
            'total_users': total_users,
            'new_users_week': new_users_week,
            'total_runners': total_runners,
            'pending_approvals': pending_approvals,
            'online_runners': online_runners,
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'completed_today': completed_today,
            'disputed_tasks': disputed_tasks,
            'total_processed': total_processed,
            'platform_revenue': platform_revenue,
            'week_revenue': week_revenue,
        },
        'recent_tasks': recent_tasks,
        'recent_signups': recent_signups,
        'top_runners': top_runners,
        'daily_data': daily_data,
        'pending_approvals_count': pending_approvals,
        'disputed_tasks_count': disputed_tasks,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ── Runner Approvals ──────────────────────────────────────────────────────────

@staff_required
def runner_approvals_view(request):
    """List all pending runner applications."""
    status_filter = request.GET.get('status', 'pending')
    runners = RunnerProfile.objects.filter(
        verification_status=status_filter
    ).select_related('user').order_by('-applied_at')

    return render(request, 'admin_panel/runner_approvals.html', {
        'runners': runners,
        'status_filter': status_filter,
        'counts': {
            'pending': RunnerProfile.objects.filter(verification_status='pending').count(),
            'approved': RunnerProfile.objects.filter(verification_status='approved').count(),
            'rejected': RunnerProfile.objects.filter(verification_status='rejected').count(),
            'suspended': RunnerProfile.objects.filter(verification_status='suspended').count(),
            'banned': RunnerProfile.objects.filter(verification_status='banned').count(),
        }
    })


@staff_required
def review_runner_view(request, runner_id):
    """Detailed review of a single runner application."""
    runner = get_object_or_404(RunnerProfile, id=runner_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            runner.verification_status = RunnerProfile.VerificationStatus.APPROVED
            runner.verified_by = request.user
            runner.verified_at = timezone.now()
            runner.save()
            # Notify user (in production: send email)
            messages.success(
                request,
                f"✅ {runner.user.full_name}'s runner application approved!"
            )

        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, "Please provide a rejection reason.")
                return redirect('admin_panel:review_runner', runner_id=runner_id)
            runner.verification_status = RunnerProfile.VerificationStatus.REJECTED
            runner.rejection_reason = reason
            runner.verified_by = request.user
            runner.verified_at = timezone.now()
            runner.save()
            messages.warning(request, f"❌ {runner.user.full_name}'s application rejected.")

        elif action == 'ban':
            runner.verification_status = RunnerProfile.VerificationStatus.BANNED
            runner.save()
            runner.user.is_active = False
            runner.user.save()
            messages.error(request, f"🚫 {runner.user.full_name} permanently banned.")

        elif action == 'unsuspend':
            runner.verification_status = RunnerProfile.VerificationStatus.APPROVED
            runner.complaint_count = 0
            runner.save()
            messages.success(request, f"Runner {runner.user.full_name} unsuspended.")

        return redirect('admin_panel:runner_approvals')

    # Task history for this runner
    task_history = Task.objects.filter(
        runner=runner.user
    ).select_related('requester', 'category').order_by('-created_at')[:20]

    return render(request, 'admin_panel/review_runner.html', {
        'runner': runner,
        'task_history': task_history,
    })


# ── Disputes ──────────────────────────────────────────────────────────────────

@staff_required
def disputes_view(request):
    """List all disputed tasks."""
    disputes = Task.objects.filter(
        status=Task.Status.DISPUTED
    ).select_related('requester', 'runner', 'category').order_by('-created_at')

    return render(request, 'admin_panel/disputes.html', {'disputes': disputes})


@staff_required
def resolve_dispute_view(request, task_id):
    """Admin resolves a dispute: release to runner or refund to requester."""
    task = get_object_or_404(Task, id=task_id, status=Task.Status.DISPUTED)

    if request.method == 'POST':
        action = request.POST.get('action')
        note = request.POST.get('note', '')

        if action == 'release_to_runner':
            from apps.payments.models import EscrowTransaction
            task.status = Task.Status.CONFIRMED
            task.confirmed_at = timezone.now()
            task.save()
            release_escrow_to_runner(task)
            messages.success(request, f"⚖️ Dispute resolved: funds released to runner.")

        elif action == 'refund_to_requester':
            from apps.payments.models import EscrowTransaction
            task.status = Task.Status.CANCELLED
            task.cancelled_by = request.user
            task.cancellation_reason = f"Admin dispute resolution: {note}"
            task.save()
            refund_escrow_to_requester(
                task,
                processed_by=request.user,
                transaction_type=EscrowTransaction.Type.DISPUTE_REFUND
            )
            messages.success(request, f"⚖️ Dispute resolved: funds refunded to requester.")

        return redirect('admin_panel:disputes')

    # Load full chat history for this task
    chat_room = getattr(task, 'chat_room', None)
    chat_messages = []
    if chat_room:
        chat_messages = Message.objects.filter(
            room=chat_room
        ).select_related('sender').order_by('created_at')

    escrow_transactions = task.escrow_transactions.all()

    return render(request, 'admin_panel/resolve_dispute.html', {
        'task': task,
        'chat_messages': chat_messages,
        'escrow_transactions': escrow_transactions,
    })


# ── User Management ───────────────────────────────────────────────────────────

@staff_required
def users_view(request):
    """List all users with search and filter."""
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')

    users = User.objects.filter(is_staff=False).select_related('wallet')

    if query:
        users = users.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(hostel_name__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    users = users.order_by('-created_at')

    return render(request, 'admin_panel/users.html', {
        'users': users,
        'query': query,
        'role_filter': role_filter,
    })


@staff_required
def ban_user_view(request, user_id):
    """Ban or unban a user."""
    user = get_object_or_404(User, id=user_id, is_staff=False)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'ban':
            user.is_active = False
            user.save()
            if hasattr(user, 'runner_profile'):
                user.runner_profile.verification_status = RunnerProfile.VerificationStatus.BANNED
                user.runner_profile.save()
            messages.error(request, f"🚫 {user.full_name} has been banned.")
        elif action == 'unban':
            user.is_active = True
            user.save()
            messages.success(request, f"✅ {user.full_name} has been unbanned.")

    return redirect('admin_panel:users')


# ── Platform Stats (AJAX) ─────────────────────────────────────────────────────

@staff_required
def live_stats_api(request):
    """Returns live platform stats as JSON for dashboard polling."""
    return JsonResponse({
        'active_tasks': Task.objects.filter(
            status__in=[Task.Status.OPEN, Task.Status.ACCEPTED, Task.Status.PICKED_UP]
        ).count(),
        'online_runners': RunnerProfile.objects.filter(is_online=True).count(),
        'pending_approvals': RunnerProfile.objects.filter(
            verification_status='pending'
        ).count(),
        'disputed_tasks': Task.objects.filter(status=Task.Status.DISPUTED).count(),
    })
