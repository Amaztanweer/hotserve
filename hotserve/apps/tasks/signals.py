"""
HotServe — Tasks Signals

Auto-creates a ChatRoom the moment a runner accepts a task.
Auto-closes the ChatRoom when the task is confirmed or cancelled.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Task


@receiver(post_save, sender=Task)
def handle_task_status_change(sender, instance, created, **kwargs):
    """
    - On ACCEPTED: create a ChatRoom between requester and runner.
    - On CONFIRMED / CANCELLED: close the ChatRoom if open.
    """
    from apps.chat.models import ChatRoom

    if created:
        return  # Nothing to do on task creation

    if instance.status == Task.Status.ACCEPTED and instance.runner:
        # Create chat room if one doesn't exist yet
        ChatRoom.objects.get_or_create(
            task=instance,
            defaults={
                'requester': instance.requester,
                'runner': instance.runner,
            }
        )

    elif instance.status in [Task.Status.CONFIRMED, Task.Status.CANCELLED]:
        # Close any active chat room
        try:
            room = instance.chat_room
            if room.status == 'active':
                room.close()
        except ChatRoom.DoesNotExist:
            pass
