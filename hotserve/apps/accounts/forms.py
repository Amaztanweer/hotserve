"""
HotServe — Accounts Forms
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from .models import User, RunnerProfile


class RequesterRegistrationForm(forms.ModelForm):
    """Registration form for new requesters."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a strong password'}),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password'})
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'hostel_name', 'room_number']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'your@college.edu'}),
            'phone': forms.TextInput(attrs={'placeholder': '9876543210'}),
            'hostel_name': forms.TextInput(attrs={'placeholder': 'e.g. Block A Hostel'}),
            'room_number': forms.TextInput(attrs={'placeholder': 'e.g. A-204'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        domain = email.split('@')[-1]
        allowed = settings.ALLOWED_COLLEGE_DOMAINS
        if not any(email.endswith(d) for d in allowed):
            raise forms.ValidationError(
                f"Only college email addresses are allowed. "
                f"Allowed domains: {', '.join(allowed)}"
            )
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.Role.REQUESTER
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='College Email',
        widget=forms.EmailInput(attrs={'placeholder': 'your@college.edu', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


class RunnerApplicationForm(forms.ModelForm):
    """
    Form for a requester to apply as a runner.
    Collects college verification info + documents.
    """

    class Meta:
        model = RunnerProfile
        fields = [
            'roll_number', 'branch', 'year_of_study',
            'college_portal_screenshot', 'selfie_with_note',
            'upi_id',
        ]
        widgets = {
            'roll_number': forms.TextInput(attrs={'placeholder': 'e.g. 21CS045'}),
            'branch': forms.TextInput(attrs={'placeholder': 'e.g. Computer Science'}),
            'year_of_study': forms.Select(choices=[(i, f'Year {i}') for i in range(1, 7)]),
            'upi_id': forms.TextInput(attrs={'placeholder': 'e.g. yourname@upi'}),
        }
        labels = {
            'college_portal_screenshot': 'College Portal Screenshot (showing your name, roll no, photo)',
            'selfie_with_note': 'Selfie holding a note with today\'s date + "HotServe Runner"',
        }

    def clean_roll_number(self):
        roll = self.cleaned_data['roll_number'].upper().strip()
        if RunnerProfile.objects.filter(roll_number=roll).exists():
            raise forms.ValidationError(
                "This roll number already has a HotServe account. "
                "One roll number = one account forever."
            )
        return roll


class ProfileUpdateForm(forms.ModelForm):
    """Update basic profile info."""

    class Meta:
        model = User
        fields = ['full_name', 'phone', 'profile_photo', 'hostel_name', 'room_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_photo'].required = False
