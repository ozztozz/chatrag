from django.urls import path
from .views import instagram_webhook

urlpatterns = [
    # Meta paneline girilecek uç nokta: https://alanadiniz.com
    path('instagram/webhook/', instagram_webhook, name='instagram_webhook'),
]
