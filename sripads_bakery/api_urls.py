from django.urls import path
from . import api_views

urlpatterns = [
    # Auth
    path('auth/register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('auth/login/', api_views.LoginAPIView.as_view(), name='api_login'),
    path('auth/profile/', api_views.ProfileAPIView.as_view(), name='api_profile'),
    
    # Products
    path('categories/', api_views.CategoryListAPIView.as_view(), name='api_categories'),
    path('products/', api_views.ProductListAPIView.as_view(), name='api_products'),
    path('products/<int:pk>/', api_views.ProductDetailAPIView.as_view(), name='api_product_detail'),
    
    # Cart
    path('cart/', api_views.CartAPIView.as_view(), name='api_cart'),
    path('cart/add/', api_views.CartAddAPIView.as_view(), name='api_cart_add'),
    path('cart/remove/', api_views.CartRemoveAPIView.as_view(), name='api_cart_remove'),
    path('cart/update/', api_views.CartUpdateAPIView.as_view(), name='api_cart_update'),
    path('cart/coupon/', api_views.CartCouponAPIView.as_view(), name='api_cart_coupon'),
    
    # Orders
    path('orders/', api_views.OrderListCreateAPIView.as_view(), name='api_orders'),
    path('orders/<str:order_number>/', api_views.OrderDetailAPIView.as_view(), name='api_order_detail'),
    path('orders/<str:order_number>/cancel/', api_views.OrderCancelAPIView.as_view(), name='api_order_cancel'),
    
    # Payments
    path('payments/webhook/<str:order_number>/', api_views.PaymentWebhookAPIView.as_view(), name='api_payment_webhook'),
    
    # Chat
    path('chat/<str:order_number>/', api_views.ChatMessageAPIView.as_view(), name='api_chat_messages'),
    
    # Feedback
    path('feedback/submit/<str:order_number>/', api_views.FeedbackSubmitAPIView.as_view(), name='api_feedback_submit'),
    path('feedback/reply/<int:pk>/', api_views.FeedbackReplyAPIView.as_view(), name='api_feedback_reply'),
    
    # Notifications
    path('notifications/', api_views.NotificationListAPIView.as_view(), name='api_notifications'),
    path('notifications/mark-read/', api_views.NotificationMarkReadAPIView.as_view(), name='api_notifications_mark_read'),
    
    # Seller Analytics
    path('seller/analytics/', api_views.SellerAnalyticsAPIView.as_view(), name='api_seller_analytics'),
]
