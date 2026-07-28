from django.urls import path
from . import views

urlpatterns = [
    path('room/<str:order_number>/', views.chat_room, name='chat_room'),
    path('api/messages/<str:order_number>/', views.get_messages, name='get_messages'),
    path('api/send/<str:order_number>/', views.send_message, name='send_message'),
]
