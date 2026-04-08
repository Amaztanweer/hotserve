from django.urls import path
from . import api_views

app_name = 'api_tasks'

urlpatterns = [
    path('', api_views.TaskListCreateAPIView.as_view(), name='list_create'),
    path('<uuid:pk>/', api_views.TaskDetailAPIView.as_view(), name='detail'),
    path('<uuid:pk>/accept/', api_views.AcceptTaskAPIView.as_view(), name='accept'),
    path('<uuid:pk>/status/', api_views.UpdateTaskStatusAPIView.as_view(), name='update_status'),
    path('categories/', api_views.CategoryListAPIView.as_view(), name='categories'),
]
