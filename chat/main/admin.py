from django.contrib import admin
from .models import InstagramUser, InstagramMessage
# Register your models here.
admin.site.register(InstagramUser)
admin.site.register(InstagramMessage)