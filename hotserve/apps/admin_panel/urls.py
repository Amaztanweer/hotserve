from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('runners/', views.runner_approvals_view, name='runner_approvals'),
    path('runners/<int:runner_id>/review/', views.review_runner_view, name='review_runner'),
    path('disputes/', views.disputes_view, name='disputes'),
    path('disputes/<uuid:task_id>/resolve/', views.resolve_dispute_view, name='resolve_dispute'),
    path('users/', views.users_view, name='users'),
    path('users/<uuid:user_id>/ban/', views.ban_user_view, name='ban_user'),
    path('api/live-stats/', views.live_stats_api, name='live_stats'),
]
