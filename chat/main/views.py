import json
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import InstagramUser, InstagramMessage

VERIFY_TOKEN = "SİZİN_BELİRLEDİĞİNİZ_VERIFY_TOKEN"
PAGE_ACCESS_TOKEN = "SİZİN_PAGE_ACCESS_TOKENINIZ"

@csrf_exempt
def instagram_webhook(request):
    # 1. DOĞRULAMA ADIMI (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Doğrulama başarısız", status=403)

    # 2. VERİ ALMA VE KAYDETME ADIMI (POST)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return HttpResponse("Geçersiz JSON", status=400)

        if data.get('object') == 'instagram':
            for entry in data.get('entry', []):
                for messaging_event in entry.get('messaging', []):
                    
                    sender_id = messaging_event.get('sender', {}).get('id')
                    
                    if 'message' in messaging_event:
                        message_data = messaging_event['message']
                        message_id = message_data.get('mid') # Meta'nın verdiği benzersiz mesaj ID'si
                        message_text = message_data.get('text')
                        
                        # 1. Kural: Mesaj metni var mı ve botun kendi mesajı (echo) değil mi?
                        if message_text and not message_data.get('is_echo'):
                            
                            # KULLANICIYI KAYDET (Yoksa oluşturur, varsa mevcut olanı getirir)
                            user_obj, created = InstagramUser.objects.get_or_create(instagram_id=sender_id)
                            
                            # GELEN MESAJI KAYDET (Aynı message_id daha önce işlenmediyse)
                            if not InstagramMessage.objects.filter(message_id=message_id).exists():
                                InstagramMessage.objects.create(
                                    user=user_obj,
                                    message_id=message_id,
                                    text=message_text,
                                    is_from_user=True
                                )
                                
                                # OTO YANIT METNİ
                                reply_text = f"Mesajınız veritabanımıza kaydedildi: '{message_text}'"
                                
                                # API Üzerinden Yanıt Gönder ve Gönderilen Yanıtı da Veritabanına Yaz
                                send_and_save_reply(user_obj, reply_text)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Yöntem Desteklenmiyor", status=405)


def send_and_save_reply(user_obj, text_content):
    """Kullanıcıya mesaj gönderir ve başarılıysa botun yanıtını da DB'ye kaydeder"""
    url = "https://facebook.com"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": user_obj.instagram_id},
        "message": {"text": text_content}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    
    try:
        response = requests.post(url, json=payload, params=params, headers=headers)
        response_data = response.json()
        
        # Eğer Meta mesajı başarıyla ilettiyse, dönen message_id ile DB'ye kaydet
        if "message_id" in response_data:
            InstagramMessage.objects.create(
                user=user_obj,
                message_id=response_data["message_id"],
                text=text_content,
                is_from_user=False # Botun yanıtı olduğunu belirtiyoruz
            )
    except requests.exceptions.RequestException as e:
        print("Mesaj gönderme/kaydetme hatası:", e)
