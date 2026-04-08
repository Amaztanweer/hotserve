"""
HotServe — Tasks Serializers & API Views
"""

from rest_framework import serializers, generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from .models import Task, TaskCategory, Rating


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    requester_name = serializers.CharField(source='requester.display_name', read_only=True)
    runner_name = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'task_number', 'title', 'description',
            'category', 'category_name', 'category_icon',
            'delivery_type', 'pickup_location', 'delivery_location',
            'reward_amount', 'platform_fee', 'runner_payout',
            'requires_purchase', 'purchase_amount',
            'status', 'is_escrow_locked',
            'requester_name', 'runner_name',
            'task_image', 'delivery_proof_image',
            'created_at', 'accepted_at', 'confirmed_at',
        ]
        read_only_fields = [
            'task_number', 'platform_fee', 'runner_payout',
            'status', 'is_escrow_locked', 'requester_name', 'runner_name',
        ]

    def get_runner_name(self, obj):
        return obj.runner.display_name if obj.runner else None


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'category', 'title', 'description', 'delivery_type',
            'pickup_location', 'delivery_location', 'reward_amount',
            'requires_purchase', 'purchase_amount', 'task_image',
        ]

    def validate_reward_amount(self, value):
        if value < 5:
            raise serializers.ValidationError("Minimum reward is ₹5.")
        return value


# ── API Views ──────────────────────────────────────────────────────────────────

class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    queryset = TaskCategory.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]


class TaskListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_runner:
            return Task.objects.filter(status=Task.Status.OPEN).exclude(requester=user)
        return Task.objects.filter(requester=user).order_by('-created_at')

    def perform_create(self, serializer):
        task = serializer.save(requester=self.request.user)
        pct = settings.PLATFORM_COMMISSION_PERCENT
        task.platform_fee = round(task.reward_amount * pct / 100, 2)
        task.runner_payout = task.reward_amount - task.platform_fee
        task.is_escrow_locked = True
        task.save()


class TaskDetailAPIView(generics.RetrieveAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.all()


class AcceptTaskAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk, status=Task.Status.OPEN)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found or already taken.'}, status=404)

        if not request.user.is_runner:
            return Response({'error': 'Must be in runner mode.'}, status=403)

        task.accept(request.user)
        return Response({'message': 'Task accepted!', 'task': TaskSerializer(task).data})


class UpdateTaskStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = generics.get_object_or_404(Task, pk=pk)
        action = request.data.get('action')

        if action == 'picked_up' and task.runner == request.user:
            task.mark_picked_up()
        elif action == 'delivered' and task.runner == request.user:
            task.mark_delivered()
        elif action == 'confirm' and task.requester == request.user:
            task.confirm()
            from apps.payments.services import release_escrow_to_runner
            release_escrow_to_runner(task)
        else:
            return Response({'error': 'Invalid action or unauthorized.'}, status=400)

        return Response({'status': task.status})
