"""
HotServe — Accounts API Views
"""

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import RunnerProfile
from .serializers import UserSerializer, WalletSerializer, RegisterSerializer, RunnerProfileSerializer


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': 'Account created successfully.', 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED
        )


class MeAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class WalletAPIView(APIView):
    def get(self, request):
        wallet = getattr(request.user, 'wallet', None)
        if not wallet:
            return Response({'error': 'Wallet not found'}, status=404)
        return Response(WalletSerializer(wallet).data)


class RunnerApplyAPIView(APIView):
    def post(self, request):
        user = request.user
        if hasattr(user, 'runner_profile'):
            return Response(
                {'error': 'Application already submitted.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RunnerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(
            {'message': 'Runner application submitted for review.'},
            status=status.HTTP_201_CREATED
        )


class ToggleAvailabilityAPIView(APIView):
    def post(self, request):
        rp = getattr(request.user, 'runner_profile', None)
        if not rp or not rp.is_approved:
            return Response({'error': 'Not an approved runner.'}, status=403)
        rp.is_available = not rp.is_available
        rp.save(update_fields=['is_available'])
        return Response({'is_available': rp.is_available})
