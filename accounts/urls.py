from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.buyer_signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('verify-login/', views.verify_login_view, name='verify_login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
