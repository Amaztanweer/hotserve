"""
HotServe — Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin (superuser only)
    path('django-admin/', admin.site.urls),

    # App routes
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.tasks.urls', namespace='tasks')),
    path('payments/', include('apps.payments.urls', namespace='payments')),
    path('chat/', include('apps.chat.urls', namespace='chat')),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),

    # REST API routes
    path('api/v1/accounts/', include('apps.accounts.api_urls', namespace='api_accounts')),
    path('api/v1/tasks/', include('apps.tasks.api_urls', namespace='api_tasks')),
    path('api/v1/payments/', include('apps.payments.api_urls', namespace='api_payments')),
    path('api/v1/chat/', include('apps.chat.api_urls', namespace='api_chat')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site branding
admin.site.site_header = '🔥 HotServe Admin'
admin.site.site_title = 'HotServe'
admin.site.index_title = 'Platform Administration'
