"""
HotServe — Chat Models

ChatRoom: Created when a runner accepts a task.
          Auto-closes after 3 hours OR when task is confirmed.
Message:  Individual messages within a room.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class ChatRoom(models.Model):
    """
    One chat room per task. Created on task acceptance.
    Closes when task is confirmed or 3 hours elapse.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', '🟢 Active'
        CLOSED = 'closed', '🔒 Closed'
        ARCHIVED = 'archived', '📁 Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(
        'tasks.Task',
        on_delete=models.CASCADE,
        related_name='chat_room'
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requester_chats'
    )
    runner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='runner_chats'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Privacy: requester can hide their photo
    requester_photo_visible = models.BooleanField(default=True)

    # Timing
    opened_at = models.DateTimeField(auto_now_add=True)
    closes_at = models.DateTimeField()   # Set to opened_at + 3 hours
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'hs_chat_rooms'
        ordering = ['-opened_at']

    def __str__(self):
        return f"Chat [{self.task.task_number}] {self.status}"

    def save(self, *args, **kwargs):
        if not self.closes_at:
            self.closes_at = timezone.now() + timezone.timedelta(
                hours=settings.CHAT_MAX_DURATION_HOURS
            )
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return (
            self.status == self.Status.ACTIVE and
            timezone.now() < self.closes_at
        )

    @property
    def time_remaining_seconds(self):
        if not self.is_active:
            return 0
        delta = self.closes_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def close(self):
        """Close the chat room (task confirmed or time expired)."""
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])

    def archive(self):
        """Archive after closing (admin can still read)."""
        self.status = self.Status.ARCHIVED
        self.save(update_fields=['status'])

    def check_and_close_if_expired(self):
        """Called periodically; closes room if 3-hour window elapsed."""
        if self.status == self.Status.ACTIVE and timezone.now() >= self.closes_at:
            self.close()
            return True
        return False


class Message(models.Model):
    """A single message in a chat room."""

    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IMAGE = 'image', 'Image'
        SYSTEM = 'system', 'System Notification'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        null=True, blank=True   # null for system messages
    )
    message_type = models.CharField(
        max_length=10, choices=MessageType.choices, default=MessageType.TEXT
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hs_messages'
        ordering = ['created_at']

    def __str__(self):
        sender = self.sender.display_name if self.sender else 'System'
        return f"[{self.room.task.task_number}] {sender}: {self.content[:40]}"
