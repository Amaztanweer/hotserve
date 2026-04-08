from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_step1_view, name='register'),
    path('register/verify/', views.register_step2_view, name='register_step2'),
    path('register/complete/', views.register_step3_view, name='register_step3'),
    path('register/resend/', views.resend_otp_view, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot/', views.forgot_step1_view, name='forgot_step1'),
    path('forgot/verify/', views.forgot_step2_view, name='forgot_step2'),
    path('forgot/reset/', views.forgot_step3_view, name='forgot_step3'),
    path('profile/', views.profile_view, name='profile'),
    path('apply-runner/', views.apply_runner_view, name='apply_runner'),
    path('switch-role/', views.switch_role_view, name='switch_role'),
]
