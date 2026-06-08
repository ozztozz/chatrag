from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_page, name='login_page'),
    path('oauth/login/', views.instagram_login, name='instagram_login'),
    path('oauth/callback/', views.instagram_callback, name='instagram_callback'),
]