from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('cart/remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # Seller panel routes
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/', views.seller_product_list, name='seller_product_list'),
    path('seller/products/add/', views.seller_product_add, name='seller_product_add'),
    path('seller/products/edit/<int:pk>/', views.seller_product_edit, name='seller_product_edit'),
    path('seller/products/delete/<int:pk>/', views.seller_product_delete, name='seller_product_delete'),
    path('seller/customers/', views.seller_customers, name='seller_customers'),
    path('seller/customers/delete/<int:customer_id>/', views.seller_delete_customer, name='seller_delete_customer'),
    path('seller/settings/', views.seller_settings, name='seller_settings'),
    path('seller/coupons/', views.seller_coupon_list, name='seller_coupon_list'),
    path('seller/coupons/add/', views.seller_coupon_add, name='seller_coupon_add'),
    path('seller/coupons/edit/<int:pk>/', views.seller_coupon_edit, name='seller_coupon_edit'),
    path('seller/coupons/delete/<int:pk>/', views.seller_coupon_delete, name='seller_coupon_delete'),
]
