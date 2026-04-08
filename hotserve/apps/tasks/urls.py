from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('post/', views.post_task_view, name='post_task'),
    path('feed/', views.task_feed_view, name='task_feed'),
    path('<uuid:pk>/', views.task_detail_view, name='task_detail'),
    path('<uuid:pk>/accept/', views.accept_task_view, name='accept_task'),
    path('<uuid:pk>/status/<str:action>/', views.update_task_status_view, name='update_status'),
]
