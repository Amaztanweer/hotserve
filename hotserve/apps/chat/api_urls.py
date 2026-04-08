from django.urls import path
from . import api_views

app_name = 'api_chat'

urlpatterns = [
    path('<uuid:room_id>/messages/', api_views.MessageListAPIView.as_view(), name='messages'),
]
