from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

app_name = 'api_accounts'

urlpatterns = [
    path('register/', api_views.RegisterAPIView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', api_views.MeAPIView.as_view(), name='me'),
    path('wallet/', api_views.WalletAPIView.as_view(), name='wallet'),
    path('runner/apply/', api_views.RunnerApplyAPIView.as_view(), name='runner_apply'),
    path('runner/toggle-availability/', api_views.ToggleAvailabilityAPIView.as_view(), name='toggle_availability'),
]
