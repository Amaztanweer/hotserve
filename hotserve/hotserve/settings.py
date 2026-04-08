"""
HotServe — Django Settings
Hostel On-Demand Delivery Platform
"""

from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production-hotserve-2024')
DEBUG=False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# ─────────────────────────────────────────────
# APPLICATIONS
# ─────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'crispy_forms',
    'crispy_bootstrap5',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.tasks',
    'apps.payments',
    'apps.chat',
    'apps.admin_panel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hotserve.urls'

# ─────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hotserve.wsgi.application'
ASGI_APPLICATION = 'hotserve.asgi.application'

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# SQLite fallback for quick local dev (comment out postgres above and use this)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# ─────────────────────────────────────────────
# REDIS & CHANNELS
# ─────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# ─────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ─────────────────────────────────────────────
# REST FRAMEWORK
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─────────────────────────────────────────────
# RAZORPAY
# ─────────────────────────────────────────────
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='rzp_test_SaMMMwIT9zQLAm')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='FbCx0ShCAJqeZd6XtKD7Pv3d')
RAZORPAY_CURRENCY = 'INR'
#rzp_test_SaMMMwIT9zQLAm
#FbCx0ShCAJqeZd6XtKD7Pv3d

# Platform commission percentage (e.g. 10 = 10%)
PLATFORM_COMMISSION_PERCENT = config('PLATFORM_COMMISSION_PERCENT', default=10, cast=int)

# ─────────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = 'HotServe <noreply@hotserve.app>'
 
# Set to empty string to allow ALL emails, or specify domains to restrict
# e.g. 'iitb.ac.in,college.edu' to restrict to college emails only
ALLOWED_COLLEGE_DOMAINS = config(
    'ALLOWED_COLLEGE_DOMAINS',
    default=''
)
# If empty, all email domains are allowed
RESTRICT_TO_COLLEGE_EMAIL = bool(ALLOWED_COLLEGE_DOMAINS)
 
# OTP settings
OTP_EXPIRY_MINUTES = 10  # OTP expires after 10 minutes
 
# ─────────────────────────────────────────────
# STATIC & MEDIA
# ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─────────────────────────────────────────────
# CRISPY FORMS
# ─────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000'
).split(',')

# ─────────────────────────────────────────────
# INTERNATIONALIZATION
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────────
# HOTSERVE BUSINESS RULES
# ─────────────────────────────────────────────
CHAT_MAX_DURATION_HOURS = 3          # Chat auto-closes after 3 hours
RUNNER_MIN_RATING_TRUSTED = 4.0      # Min rating for Trusted Runner
RUNNER_MIN_TASKS_TRUSTED = 10        # Min tasks for Trusted Runner
RUNNER_MIN_RATING_ELITE = 4.5        # Min rating for Elite Runner
RUNNER_MIN_TASKS_ELITE = 50          # Min tasks for Elite Runner
AUTO_SUSPEND_COMPLAINT_COUNT = 3     # Complaints before auto-suspend
TASK_AUTO_CANCEL_MINUTES = 15        # Minutes before unaccepted task auto-cancels
WALLET_MIN_TOPUP = 10                # Minimum wallet top-up in INR
WALLET_MAX_BALANCE = 5000            # Maximum wallet balance in INR

#print("EMAIL_BACKEND:", config('EMAIL_BACKEND'))