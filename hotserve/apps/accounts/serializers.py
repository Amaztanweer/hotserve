"""
HotServe — Accounts API Serializers
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, RunnerProfile, Wallet


class UserSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    trust_level = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone',
            'profile_photo', 'role', 'hostel_name', 'room_number',
            'is_verified_email', 'created_at', 'wallet_balance', 'trust_level'
        ]
        read_only_fields = ['id', 'email', 'created_at']

    def get_wallet_balance(self, obj):
        wallet = getattr(obj, 'wallet', None)
        return str(wallet.balance) if wallet else '0.00'

    def get_trust_level(self, obj):
        rp = getattr(obj, 'runner_profile', None)
        return rp.trust_level if rp else None


class RunnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = RunnerProfile
        fields = [
            'id', 'user', 'roll_number', 'branch', 'year_of_study',
            'verification_status', 'trust_level', 'total_tasks_completed',
            'average_rating', 'total_ratings_count', 'total_earnings',
            'upi_id', 'is_online', 'is_available', 'applied_at'
        ]
        read_only_fields = [
            'verification_status', 'trust_level', 'total_tasks_completed',
            'average_rating', 'total_ratings_count', 'total_earnings'
        ]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['balance', 'total_topped_up', 'total_spent', 'updated_at']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'hostel_name', 'room_number',
                  'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
