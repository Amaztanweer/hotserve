from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('<uuid:room_id>/', views.chat_room_view, name='room'),
    path('<uuid:room_id>/close/', views.close_chat_view, name='close'),
]
