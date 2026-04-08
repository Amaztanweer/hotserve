"""
HotServe — Chat Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import ChatRoom, Message
from apps.tasks.models import Task


@login_required
def chat_room_view(request, room_id):
    """Main chat UI for a task conversation."""
    room = get_object_or_404(ChatRoom, id=room_id)
    user = request.user

    # Only requester and runner can access
    if user not in [room.requester, room.runner]:
        messages.error(request, "You don't have access to this chat.")
        return redirect('tasks:dashboard')

    # Load message history
    chat_messages = Message.objects.filter(
        room=room
    ).select_related('sender').order_by('created_at')

    # Mark messages as read
    Message.objects.filter(room=room, is_read=False).exclude(sender=user).update(is_read=True)

    is_requester = user == room.requester

    return render(request, 'chat/room.html', {
        'room': room,
        'messages': chat_messages,
        'task': room.task,
        'is_requester': is_requester,
        'other_user': room.runner if is_requester else room.requester,
    })


@login_required
def close_chat_view(request, room_id):
    """Requester ends chat early."""
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user != room.requester:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if room.is_active:
        room.close()
        Message.objects.create(
            room=room,
            sender=None,
            message_type=Message.MessageType.SYSTEM,
            content="Chat was ended early by the requester."
        )

    return redirect('tasks:task_detail', pk=room.task.pk)
