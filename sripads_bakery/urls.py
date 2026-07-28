from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('orders/', include('orders.urls')),
    path('chat/', include('chat.urls')),
    path('feedback/', include('feedback.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/', include('sripads_bakery.api_urls')), # REST API routes
    path('', include('bakery.urls')), # Core bakery routes (Homepage, Product list, cart)
]

from bakery.views import serve_db_media
from django.urls import re_path

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files from the database or fall back to local disk
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_db_media),
]
