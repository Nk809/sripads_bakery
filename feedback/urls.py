from django.urls import path
from . import views

urlpatterns = [
    path('submit/<str:order_number>/', views.submit_feedback, name='submit_feedback'),
    path('reply/<int:feedback_id>/', views.seller_reply_feedback, name='seller_reply_feedback'),
]
