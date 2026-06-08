from django.db import models

# Create your models here.
class UserAccount(models.Model):
    instagram_user_id = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=500)
    username = models.CharField(max_length=255, blank=True, null=True)  
    profile_picture_url = models.URLField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)