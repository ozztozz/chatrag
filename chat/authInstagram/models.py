from django.db import models
from django.utils import timezone

# Create your models here.
class UserAccount(models.Model):
    instagram_user_id = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=500)
    username = models.CharField(max_length=255, blank=True, null=True)  
    profile_picture_url = models.URLField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    token_error = models.TextField(blank=True)

    def token_is_expired(self):
        return bool(self.token_expires_at and self.token_expires_at <= timezone.now())