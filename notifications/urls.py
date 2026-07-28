from django.urls import path
from . import views

urlpatterns = [
    path('api/list/', views.get_notifications, name='get_notifications'),
    path('api/mark-read/', views.mark_as_read, name='mark_notifications_read'),
]
