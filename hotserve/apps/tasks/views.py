"""
HotServe — Tasks Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.conf import settings
from .models import Task, TaskCategory, Rating
from .forms import TaskCreateForm, RatingForm
from apps.payments.models import EscrowTransaction, WalletTransaction


@login_required
def dashboard_view(request):
    """
    Main dashboard — different view for requester vs runner.
    """
    user = request.user

    if user.is_runner:
        # Runner dashboard: show open tasks they can accept
        runner_profile = getattr(user, 'runner_profile', None)
        trust_level = runner_profile.trust_level if runner_profile else 'new'

        open_tasks = Task.objects.filter(
            status=Task.Status.OPEN
        ).exclude(requester=user).select_related('requester', 'category')

        # Filter by trust level requirements
        if trust_level == 'new':
            open_tasks = open_tasks.filter(category__min_trust_required='new')

        my_active = Task.objects.filter(
            runner=user,
            status__in=[Task.Status.ACCEPTED, Task.Status.PICKED_UP]
        ).select_related('requester', 'category')

        context = {
            'open_tasks': open_tasks[:20],
            'my_active_tasks': my_active,
            'runner_profile': runner_profile,
            'mode': 'runner',
        }
    else:
        # Requester dashboard
        my_tasks = Task.objects.filter(
            requester=user
        ).select_related('runner', 'category').order_by('-created_at')

        active_tasks = my_tasks.filter(
            status__in=[Task.Status.OPEN, Task.Status.ACCEPTED, Task.Status.PICKED_UP]
        )
        past_tasks = my_tasks.filter(
            status__in=[Task.Status.CONFIRMED, Task.Status.CANCELLED]
        )[:10]

        context = {
            'active_tasks': active_tasks,
            'past_tasks': past_tasks,
            'categories': TaskCategory.objects.filter(is_active=True),
            'wallet': getattr(user, 'wallet', None),
            'mode': 'requester',
        }

    return render(request, 'tasks/dashboard.html', context)


@login_required
def post_task_view(request):
    """Requester posts a new task."""
    if request.user.is_runner:
        messages.warning(request, "Switch to Requester mode to post tasks.")
        return redirect('tasks:dashboard')

    if request.method == 'POST':
        form = TaskCreateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                task = form.save(commit=False)
                task.requester = request.user

                # Calculate fees
                pct = settings.PLATFORM_COMMISSION_PERCENT
                task.platform_fee = round(task.reward_amount * pct / 100, 2)
                task.runner_payout = task.reward_amount - task.platform_fee

                if not task.purchase_amount:
                    task.purchase_amount = task.reward_amount

                # Set expiry
                task.expires_at = timezone.now() + timezone.timedelta(
                    minutes=settings.TASK_AUTO_CANCEL_MINUTES
                )

                # Lock funds in wallet
                wallet = request.user.wallet
                total = task.total_locked_amount
                if not wallet.can_afford(total):
                    messages.error(
                        request,
                        f"Insufficient wallet balance. "
                        f"Need ₹{total}, have ₹{wallet.balance}. "
                        f"Please top up your wallet."
                    )
                    return render(request, 'tasks/post_task.html', {'form': form})

                wallet.deduct(total)
                task.is_escrow_locked = True
                task.save()

                # Record escrow transaction
                EscrowTransaction.objects.create(
                    task=task,
                    amount=total,
                    transaction_type=EscrowTransaction.Type.LOCK,
                    description=f"Escrow locked for task {task.task_number}"
                )

                messages.success(
                    request,
                    f"Task posted! 🔥 Task #{task.task_number} is now live. "
                    f"₹{total} locked from your wallet."
                )
                return redirect('tasks:task_detail', pk=task.pk)
    else:
        form = TaskCreateForm()

    return render(request, 'tasks/post_task.html', {
        'form': form,
        'categories': TaskCategory.objects.filter(is_active=True),
        'wallet': getattr(request.user, 'wallet', None),
    })


@login_required
def task_detail_view(request, pk):
    """Detail page for a single task."""
    task = get_object_or_404(Task, pk=pk)
    user = request.user
    is_requester = task.requester == user
    is_runner = task.runner == user
    can_view = is_requester or is_runner or user.is_staff

    if not can_view and task.status == Task.Status.OPEN:
        can_view = True  # Open tasks visible to all runners

    if not can_view:
        messages.error(request, "You don't have permission to view this task.")
        return redirect('tasks:dashboard')

    # Check if rating exists
    rating = getattr(task, 'rating', None)
    rating_form = None
    if task.status == Task.Status.CONFIRMED and is_requester and not rating:
        if request.method == 'POST' and 'submit_rating' in request.POST:
            rating_form = RatingForm(request.POST)
            if rating_form.is_valid():
                r = rating_form.save(commit=False)
                r.task = task
                r.rated_by = user
                r.runner = task.runner
                r.save()
                messages.success(request, "Rating submitted! ⭐ Thank you.")
                return redirect('tasks:task_detail', pk=pk)
        else:
            rating_form = RatingForm()

    context = {
        'task': task,
        'is_requester': is_requester,
        'is_runner': is_runner,
        'rating': rating,
        'rating_form': rating_form,
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def accept_task_view(request, pk):
    """Runner accepts an open task."""
    task = get_object_or_404(Task, pk=pk, status=Task.Status.OPEN)
    user = request.user

    if not user.is_runner:
        messages.error(request, "Switch to Runner mode to accept tasks.")
        return redirect('tasks:dashboard')

    runner_profile = getattr(user, 'runner_profile', None)
    if not runner_profile or not runner_profile.is_approved:
        messages.error(request, "Your runner account is not approved yet.")
        return redirect('tasks:dashboard')

    if task.requester == user:
        messages.error(request, "You cannot accept your own task.")
        return redirect('tasks:task_detail', pk=pk)

    # Check trust level requirement
    cat = task.category
    tl = runner_profile.trust_level
    if cat.min_trust_required == 'trusted' and tl == 'new':
        messages.error(request, "This task requires a Trusted Runner or higher.")
        return redirect('tasks:task_detail', pk=pk)
    if cat.min_trust_required == 'elite' and tl != 'elite':
        messages.error(request, "This task requires an Elite Runner.")
        return redirect('tasks:task_detail', pk=pk)

    task.accept(user)
    messages.success(
        request,
        f"You've accepted task #{task.task_number}! 🏃 "
        f"Head to {task.pickup_location} and pick it up."
    )
    return redirect('tasks:task_detail', pk=pk)


@login_required
def update_task_status_view(request, pk, action):
    """
    Runner updates task status: picked_up → delivered.
    Requester confirms delivery.
    """
    task = get_object_or_404(Task, pk=pk)
    user = request.user

    with transaction.atomic():
        if action == 'picked_up' and task.runner == user:
            if task.status != Task.Status.ACCEPTED:
                messages.error(request, "Task is not in accepted state.")
                return redirect('tasks:task_detail', pk=pk)
            task.mark_picked_up()
            messages.success(request, "Marked as picked up! 📦 Deliver it now.")

        elif action == 'delivered' and task.runner == user:
            if task.status != Task.Status.PICKED_UP:
                messages.error(request, "Task must be picked up first.")
                return redirect('tasks:task_detail', pk=pk)
            if 'proof_image' in request.FILES:
                task.delivery_proof_image = request.FILES['proof_image']
            task.mark_delivered()
            messages.success(request, "Marked as delivered! ✅ Waiting for requester to confirm.")

        elif action == 'confirm' and task.requester == user:
            if task.status != Task.Status.DELIVERED:
                messages.error(request, "Task has not been delivered yet.")
                return redirect('tasks:task_detail', pk=pk)
            task.confirm()

            # Release escrow to runner
            from apps.payments.services import release_escrow_to_runner
            release_escrow_to_runner(task)

            messages.success(
                request,
                f"Delivery confirmed! 🎉 ₹{task.runner_payout} sent to the runner."
            )

        elif action == 'dispute' and task.requester == user:
            task.raise_dispute()
            messages.warning(
                request,
                "Dispute raised. ⚠️ Our admin will review this within 24 hours."
            )

        elif action == 'cancel' and task.requester == user:
            if task.status not in [Task.Status.OPEN]:
                messages.error(request, "Cannot cancel a task that has been accepted.")
                return redirect('tasks:task_detail', pk=pk)
            reason = request.POST.get('cancel_reason', '')
            task.cancel(user, reason)

            # Refund wallet
            wallet = user.wallet
            wallet.credit(task.total_locked_amount)
            EscrowTransaction.objects.create(
                task=task,
                amount=task.total_locked_amount,
                transaction_type=EscrowTransaction.Type.REFUND,
                description=f"Refund for cancelled task {task.task_number}"
            )
            messages.info(request, f"Task cancelled. ₹{task.total_locked_amount} refunded to wallet.")

        else:
            messages.error(request, "Invalid action.")

    return redirect('tasks:task_detail', pk=pk)


@login_required
def task_feed_view(request):
    """Full task feed for runners."""
    if not request.user.is_runner:
        return redirect('tasks:dashboard')

    runner_profile = getattr(request.user, 'runner_profile', None)
    trust_level = runner_profile.trust_level if runner_profile else 'new'

    tasks = Task.objects.filter(
        status=Task.Status.OPEN
    ).exclude(
        requester=request.user
    ).select_related('requester', 'category').order_by('-created_at')

    if trust_level == 'new':
        tasks = tasks.filter(category__min_trust_required='new')

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        tasks = tasks.filter(category_id=category_id)

    return render(request, 'tasks/task_feed.html', {
        'tasks': tasks,
        'categories': TaskCategory.objects.filter(is_active=True),
        'selected_category': category_id,
        'runner_profile': runner_profile,
    })
