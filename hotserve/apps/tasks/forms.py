"""
HotServe — Tasks Forms
"""

from django import forms
from .models import Task, TaskCategory, Rating


class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'category', 'title', 'description',
            'delivery_type', 'pickup_location', 'delivery_location',
            'reward_amount', 'requires_purchase', 'purchase_amount',
            'task_image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Get me a burger from Canteen B'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Specific instructions, item details, etc.'
            }),
            'pickup_location': forms.TextInput(attrs={
                'placeholder': 'e.g. Main Canteen, Block B Ground Floor'
            }),
            'delivery_location': forms.TextInput(attrs={
                'placeholder': 'e.g. Block A, Room 204'
            }),
            'reward_amount': forms.NumberInput(attrs={
                'min': 5, 'step': 5,
                'placeholder': '₹ Reward for runner'
            }),
            'purchase_amount': forms.NumberInput(attrs={
                'min': 0, 'step': 1,
                'placeholder': '₹ Amount for runner to spend'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TaskCategory.objects.filter(is_active=True)
        self.fields['task_image'].required = False
        self.fields['purchase_amount'].required = False

    def clean(self):
        cleaned = super().clean()
        requires_purchase = cleaned.get('requires_purchase')
        purchase_amount = cleaned.get('purchase_amount', 0)
        if requires_purchase and (not purchase_amount or purchase_amount <= 0):
            raise forms.ValidationError(
                "Please enter the purchase amount if the runner needs to buy something."
            )
        return cleaned


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['stars', 'comment']
        widgets = {
            'stars': forms.RadioSelect(choices=[(i, f'{"⭐" * i}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Optional feedback for the runner...'
            }),
        }
