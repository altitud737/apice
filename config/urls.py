from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from crm.whatsapp_views import whatsapp_webhook
from crm.integrations_mercadolibre_views import mercadolibre_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Allauth URLs (login, signup, OAuth)
    path('superadmin/', include('accounts.urls')),  # Panel de super administrador
    
    # Webhooks (must be before crm URLs to avoid conflicts)
    path('webhook/whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),
    path('webhooks/mercadolibre/', mercadolibre_webhook, name='mercadolibre_webhook'),
    
    path('', include('crm.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
