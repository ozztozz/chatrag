from django.db import models

class InstagramUser(models.Model):
    # Meta'nın verdiği benzersiz kullanıcı ID'si (IGSID)
    instagram_id = models.CharField(max_length=100, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User: {self.instagram_id}"

class InstagramMessage(models.Model):
    # Mesajı gönderen kullanıcı ile ilişki
    user = models.ForeignKey(InstagramUser, on_delete=models.CASCADE, related_name='messages')
    # Mesajın benzersiz Meta ID'si (Aynı mesajın tekrar kaydedilmesini önler)
    message_id = models.CharField(max_length=255, unique=True)
    # Mesaj içeriği
    text = models.TextField(blank=True, null=True)
    # Mesajın yönü (Kullanıcıdan gelen mi, yoksa bota ait bir yanıt mı?)
    is_from_user = models.BooleanField(default=True)
    # Kayıt tarihi
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']  # En yeni mesaj en üstte görünür

    def __str__(self):
        sender = "User" if self.is_from_user else "Bot"
        return f"{sender}: {self.text[:30]}"
