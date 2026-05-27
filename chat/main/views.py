import json
from distro import name
from google import genai
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import InstagramUser, InstagramMessage
from google.genai import types
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from google.genai.errors import ClientError
import time
INSTAGRAM_ACCESS_TOKEN = settings.INSTAGRAM_ACCESS_TOKEN
GEMINI_API_KEY = settings.GEMINI_API_KEY
with staticfiles_storage.open('knowledge.txt') as f:
        KNOWLEDGE = f.read().decode('utf-8')
with staticfiles_storage.open('promt.txt') as f:
        PROMT = f.read().decode('utf-8')


def get_old_messages(user_obj, limit=10):

    data = KNOWLEDGE
    eski_mesajlar = []
    eski_mesajlar.append(
        types.Content(
            role='user',
            parts=[types.Part.from_text(text=data)]
        )
    )
    old_messages_data = InstagramMessage.objects.filter(user=user_obj).order_by('-timestamp')[:limit]
 
    prev_role = None
    prev_text = None
    if old_messages_data:
        for msg in reversed(old_messages_data):  # kronolojik sıraya çevir
            role = "user" if msg.is_from_user else "model"
            if role == prev_role == "user":
                # Önceki user mesajına ekle
                prev_text += "\n" + msg.text
            else:
                if prev_role is not None:
                    eski_mesajlar.append(types.Content(
                        role=prev_role,
                        parts=[types.Part.from_text(text=prev_text)]
                    ))
                prev_role = role
                prev_text = msg.text
        # Son mesajı ekle
        if prev_role is not None:
            eski_mesajlar.append(types.Content(
                role=prev_role,
                parts=[types.Part.from_text(text=prev_text)]
            ))
        
    return eski_mesajlar

def get_gemini_messages(user_obj,new_message ,limit=10):
    name= user_obj.name if user_obj.name else "Değerli Velimiz"
    name_part = f"Kullanıcının adı {name.title()}. Konuşma sırasında kullanıcıya ismiyle hitap et ve samimi/profesyonel bir dil kullan."

    prompt = PROMT+name_part
    
    client = genai.Client(api_key=GEMINI_API_KEY)


    old_messages_data = get_old_messages(user_obj, limit=limit)
    chat = client.chats.create(
            model="gemini-2.5-flash-lite",
            history=old_messages_data,
            config=types.GenerateContentConfig(
                system_instruction=prompt, # Sistem promptu buraya eklenir
                temperature=0.3 # Bilgi tabanına sadık kalması için yaratıcılığı düşürdük
            )
        )
    for i in range(0,2):
        
        try:
            response = chat.send_message(new_message)  # Son user mesajını gönderiyoruz
            
        except ClientError as e:
                # 429 durum kodunu kontrol ediyoruz (Resource Exhausted)
            if e.code == 429:
                time.sleep(i * 20)  # 30 saniye bekle
                continue
        else:
            break
    return response.text

def get_instagram_user_info(instagram_id):
    url = f"https://graph.instagram.com/v25.0/{instagram_id}?fields=name,username,is_user_follow_business&access_token={INSTAGRAM_ACCESS_TOKEN}"
    response=requests.get(url)
    metadata=response.json()
    return metadata

@csrf_exempt
def instagram_webhook(request):
    # 1. DOĞRULAMA ADIMI (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == 'alphaacademyverifytoken' :
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
                            if created or user_obj.name is None:  # Yeni kullanıcıysa veya adı yoksa bilgileri çek
                                try:
                                    user_info = get_instagram_user_info(sender_id)
                                    user_obj.name = user_info.get('name')
                                    user_obj.username = user_info.get('username')
                                    user_obj.is_user_follow_business = user_info.get('is_user_follow_business', False)
                                    user_obj.save()
                                except Exception as e:
                                   pass
                            if user_obj.is_user_follow_business:
                                return HttpResponse("EVENT_RECEIVED", status=200) # Takip eden kullanıcılar için yanıt vermiyoruz
                            
                            reply_text = get_gemini_messages(user_obj, message_text)  
                            
                            # GELEN MESAJI KAYDET (Aynı message_id daha önce işlenmediyse)
                            if not InstagramMessage.objects.filter(message_id=message_id).exists():
                                InstagramMessage.objects.create(
                                    user=user_obj,
                                    message_id=message_id,
                                    text=message_text,
                                    is_from_user=True
                                )
                                
                                # OTO YANIT METNİ
                                 
                                # API Üzerinden Yanıt Gönder ve Gönderilen Yanıtı da Veritabanına Yaz
                                send_and_save_reply(user_obj, reply_text)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Yöntem Desteklenmiyor", status=405)




def send_and_save_reply(user_obj, text_content):
    """Kullanıcıya mesaj gönderir ve başarılıysa botun yanıtını da DB'ye kaydeder"""
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {f'Authorization': f'Bearer {INSTAGRAM_ACCESS_TOKEN}',
           'Content-Type': 'application/json'
 }
    payload = {
        "recipient": {"id": user_obj.instagram_id},
        "message": {"text": text_content}
    }
    
    try:
        response=requests.post(url,headers=headers,json=payload)
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
        with open("api.txt", "a") as f:
            f.write(f"API İstek Hatası: {e}\n")
        
