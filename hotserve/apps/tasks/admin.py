from django.contrib import admin
from .models import Task, TaskCategory, Rating


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'base_reward_min', 'base_reward_max', 'min_trust_required', 'is_active', 'sort_order']
    list_editable = ['is_active', 'sort_order']
    list_display_links = ['name']

    def get_list_display(self, request):
        return self.list_display + ['sort_order']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_number', 'title', 'category', 'status',
        'requester', 'runner', 'reward_amount', 'created_at'
    ]
    list_filter = ['status', 'category', 'delivery_type']
    search_fields = ['task_number', 'title', 'requester__email', 'runner__email']
    readonly_fields = [
        'task_number', 'platform_fee', 'runner_payout',
        'created_at', 'accepted_at', 'confirmed_at'
    ]
    date_hierarchy = 'created_at'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['task', 'runner', 'rated_by', 'stars', 'created_at']
    list_filter = ['stars']
