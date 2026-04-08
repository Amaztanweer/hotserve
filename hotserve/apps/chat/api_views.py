from rest_framework import generics, serializers
from .models import Message, ChatRoom


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.display_name', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'sender_name', 'message_type', 'is_read', 'created_at']


class MessageListAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        user = self.request.user
        try:
            room = ChatRoom.objects.get(id=room_id)
            if user not in [room.requester, room.runner]:
                return Message.objects.none()
            return Message.objects.filter(room=room).order_by('created_at')
        except ChatRoom.DoesNotExist:
            return Message.objects.none()
