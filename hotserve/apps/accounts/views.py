"""
HotServe — Accounts Views
Registration with OTP, Login, Password Reset with OTP
"""
 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import User, RunnerProfile, Wallet, OTPCode
from .forms import ProfileUpdateForm, RunnerApplicationForm
from .email_utils import send_otp_email
 
 
# ── REGISTRATION (3 steps: email → OTP verify → set password) ────────────────
 
def register_step1_view(request):
    """Step 1 — Enter email, send OTP."""
    if request.user.is_authenticated:
        return redirect('tasks:dashboard')
 
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        full_name = request.POST.get('full_name', '').strip()
 
        if not email or not full_name:
            messages.error(request, "Please enter your name and email.")
            return render(request, 'accounts/register_step1.html')
 
        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'accounts/register_step1.html')
 
        otp = OTPCode.generate(email, OTPCode.Purpose.REGISTRATION)
        sent = send_otp_email(email, otp.code, 'registration')
 
        if not sent:
            messages.error(request, "Failed to send email. Check your email address.")
            return render(request, 'accounts/register_step1.html')
 
        request.session['reg_email'] = email
        request.session['reg_full_name'] = full_name
 
        messages.success(request, f"OTP sent to {email}. Check your inbox.")
        return redirect('accounts:register_step2')
 
    return render(request, 'accounts/register_step1.html')
 
 
def register_step2_view(request):
    """Step 2 — Enter OTP to verify email."""
    if request.user.is_authenticated:
        return redirect('tasks:dashboard')
 
    email = request.session.get('reg_email')
    if not email:
        return redirect('accounts:register')
 
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        valid, error = OTPCode.verify(email, code, OTPCode.Purpose.REGISTRATION)
 
        if not valid:
            messages.error(request, error)
            return render(request, 'accounts/register_step2.html', {'email': email})
 
        request.session['reg_email_verified'] = True
        return redirect('accounts:register_step3')
 
    return render(request, 'accounts/register_step2.html', {'email': email})
 
 
def register_step3_view(request):
    """Step 3 — Set password and complete registration."""
    if request.user.is_authenticated:
        return redirect('tasks:dashboard')
 
    email = request.session.get('reg_email')
    full_name = request.session.get('reg_full_name')
    verified = request.session.get('reg_email_verified')
 
    if not email or not verified:
        return redirect('accounts:register')
 
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        phone = request.POST.get('phone', '').strip()
        hostel_name = request.POST.get('hostel_name', '').strip()
        room_number = request.POST.get('room_number', '').strip()
 
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'accounts/register_step3.html', {'email': email, 'full_name': full_name})
 
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/register_step3.html', {'email': email, 'full_name': full_name})
 
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
                hostel_name=hostel_name,
                room_number=room_number,
                is_verified_email=True,
            )
 
        for key in ['reg_email', 'reg_full_name', 'reg_email_verified']:
            request.session.pop(key, None)
 
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f"Welcome to HotServe, {user.display_name}! 🔥")
        return redirect('tasks:dashboard')
 
    return render(request, 'accounts/register_step3.html', {'email': email, 'full_name': full_name})
 
 
def resend_otp_view(request):
    """Resend OTP."""
    if request.session.get('reg_email'):
        email = request.session.get('reg_email')
        purpose = OTPCode.Purpose.REGISTRATION
        redirect_to = 'accounts:register_step2'
    else:
        email = request.session.get('reset_email')
        purpose = OTPCode.Purpose.PASSWORD_RESET
        redirect_to = 'accounts:forgot_step2'
 
    if not email:
        return redirect('accounts:register')
 
    otp = OTPCode.generate(email, purpose)
    send_otp_email(email, otp.code, purpose.value)
    messages.success(request, f"New OTP sent to {email}.")
    return redirect(redirect_to)
 
 
# ── LOGIN ─────────────────────────────────────────────────────────────────────
 
def login_view(request):
    if request.user.is_authenticated:
        return redirect('tasks:dashboard')
 
    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
 
        if user:
            login(request, user)
            user.update_last_seen()
            return redirect(request.GET.get('next', 'tasks:dashboard'))
        else:
            messages.error(request, "Invalid email or password.")
 
    return render(request, 'accounts/login.html')
 
 
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You've been logged out.")
    return redirect('accounts:login')
 
 
# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────
 
def forgot_step1_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
 
        if User.objects.filter(email=email, is_active=True).exists():
            otp = OTPCode.generate(email, OTPCode.Purpose.PASSWORD_RESET)
            send_otp_email(email, otp.code, 'password_reset')
            request.session['reset_email'] = email
 
        messages.success(request, f"If {email} is registered, an OTP has been sent.")
        return redirect('accounts:forgot_step2')
 
    return render(request, 'accounts/forgot_step1.html')
 
 
def forgot_step2_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('accounts:forgot_step1')
 
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        valid, error = OTPCode.verify(email, code, OTPCode.Purpose.PASSWORD_RESET)
 
        if not valid:
            messages.error(request, error)
            return render(request, 'accounts/forgot_step2.html', {'email': email})
 
        request.session['reset_verified'] = True
        return redirect('accounts:forgot_step3')
 
    return render(request, 'accounts/forgot_step2.html', {'email': email})
 
 
def forgot_step3_view(request):
    email = request.session.get('reset_email')
    verified = request.session.get('reset_verified')
 
    if not email or not verified:
        return redirect('accounts:forgot_step1')
 
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
 
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'accounts/forgot_step3.html')
 
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/forgot_step3.html')
 
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()
 
        for key in ['reset_email', 'reset_verified']:
            request.session.pop(key, None)
 
        messages.success(request, "Password reset successfully! Please log in.")
        return redirect('accounts:login')
 
    return render(request, 'accounts/forgot_step3.html')

@login_required
def profile_view(request):
    """View & edit user profile."""
    user = request.user
    wallet = getattr(user, 'wallet', None)
    runner_profile = getattr(user, 'runner_profile', None)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=user)

    context = {
        'form': form,
        'wallet': wallet,
        'runner_profile': runner_profile,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def apply_runner_view(request):
    user = request.user

    # Already has a runner profile
    if hasattr(user, 'runner_profile'):
        rp = user.runner_profile
        if rp.verification_status == RunnerProfile.VerificationStatus.APPROVED:
            messages.info(request, "You are already an approved runner!")
        elif rp.verification_status == RunnerProfile.VerificationStatus.PENDING:
            messages.info(request, "Your runner application is under review. We'll notify you soon.")
        elif rp.verification_status == RunnerProfile.VerificationStatus.REJECTED:
            messages.warning(
                request,
                f"Your previous application was rejected: {rp.rejection_reason}. "
                f"Please contact support."
            )
        elif rp.verification_status == RunnerProfile.VerificationStatus.BANNED:
            messages.error(request, "Your runner account has been permanently banned.")
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = RunnerApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                runner_profile = form.save(commit=False)
                runner_profile.user = user
                runner_profile.save()
                messages.success(
                    request,
                    "Application submitted! ✅ Our admin will review it within 24 hours."
                )
                return redirect('accounts:profile')
    else:
        form = RunnerApplicationForm()

    # ✅ ADD THIS PART
    steps = [
        {"num": 1, "icon": "📝", "label": "Fill form"},
        {"num": 2, "icon": "📸", "label": "Upload proof"},
        {"num": 3, "icon": "🔍", "label": "Admin reviews"},
        {"num": 4, "icon": "✅", "label": "Go live"},
    ]

    return render(request, 'accounts/apply_runner.html', {
        'form': form,
        'steps': steps
    })

@login_required
def switch_role_view(request):
    """
    Approved runners can switch between REQUESTER and RUNNER mode.
    """
    user = request.user
    runner_profile = getattr(user, 'runner_profile', None)

    if not runner_profile or not runner_profile.is_approved:
        messages.error(request, "You must be an approved runner to switch roles.")
        return redirect('tasks:dashboard')

    if user.role == User.Role.REQUESTER:
        user.role = User.Role.RUNNER
        messages.success(request, "Switched to Runner mode 🏃 You can now accept tasks.")
    else:
        user.role = User.Role.REQUESTER
        messages.success(request, "Switched to Requester mode 📋 You can now post tasks.")

    user.save(update_fields=['role'])
    return redirect('tasks:dashboard')
