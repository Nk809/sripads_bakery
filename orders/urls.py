from django.urls import path
from . import views
from feedback import views as feedback_views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<str:order_number>/', views.payment_page, name='payment_page'),
    path('payment-success/<str:order_number>/', views.payment_success_webhook, name='payment_success'),
    path('payu-success/<str:order_number>/', views.payu_success_callback, name='payu_success_callback'),
    path('payu-failure/<str:order_number>/', views.payu_failure_callback, name='payu_failure_callback'),
    path('payment-remaining/<str:order_number>/', views.payment_remaining_page, name='payment_remaining_page'),
    path('payment-remaining-success/<str:order_number>/', views.payment_remaining_success, name='payment_remaining_success'),
    path('track/<str:order_number>/', views.order_tracking, name='order_tracking'),
    path('history/', views.order_history, name='order_history'),
    path('invoice/<str:order_number>/', views.download_invoice, name='download_invoice'),
    path('cancel/<str:order_number>/', views.cancel_order, name='cancel_order'),
    path('reorder/<str:order_number>/', views.reorder, name='reorder'),
    
    # Seller order management
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/manage/', views.seller_orders, name='seller_orders'),
    path('seller/orders/status/<str:order_number>/', views.seller_update_order_status, name='seller_update_order_status'),
    path('seller/orders/cancel/<str:order_number>/', views.seller_cancel_order, name='seller_cancel_order'),
    path('seller/orders/delivery-charge/<str:order_number>/', views.seller_set_delivery_charge, name='seller_set_delivery_charge'),
    path('seller/payment/verify/<int:payment_id>/', views.seller_verify_payment, name='seller_verify_payment'),
    path('seller/feedback/', feedback_views.seller_feedback_list, name='seller_feedback_list'),
]
