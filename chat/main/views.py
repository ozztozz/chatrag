import json
from google import genai
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import InstagramUser, InstagramMessage
from google.genai import types
import os
from django.conf import settings



def get_old_messages(user_obj, limit=10):
    knowledge_file_path = os.path.join(settings.BASE_DIR, 'main', 'alpha_chat.txt')
    with open(knowledge_file_path, "r", encoding="utf-8") as f:
        data = f.read()
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
    prompt_file_path = os.path.join(settings.BASE_DIR, 'main', 'alpha_prompt.txt')
    
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    client = genai.Client(api_key='AIzaSyCAIjIN1mdXHNZgxknmcSMlb_TQIytquCI')


    old_messages_data = get_old_messages(user_obj, limit=limit)
    chat = client.chats.create(
            model="gemini-2.5-flash",
            history=old_messages_data,
            config=types.GenerateContentConfig(
                system_instruction=prompt, # Sistem promptu buraya eklenir
                temperature=0.3 # Bilgi tabanına sadık kalması için yaratıcılığı düşürdük
            )
        )
    response = chat.send_message(new_message)  # Son user mesajını gönderiyoruz
    return response.text


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
                            
                            # GELEN MESAJI KAYDET (Aynı message_id daha önce işlenmediyse)
                            if not InstagramMessage.objects.filter(message_id=message_id).exists():
                                InstagramMessage.objects.create(
                                    user=user_obj,
                                    message_id=message_id,
                                    text=message_text,
                                    is_from_user=True
                                )
                                
                                # OTO YANIT METNİ
                                reply_text = get_gemini_messages(user_obj, message_text)    
                                # API Üzerinden Yanıt Gönder ve Gönderilen Yanıtı da Veritabanına Yaz
                                send_and_save_reply(user_obj, reply_text)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Yöntem Desteklenmiyor", status=405)




def send_and_save_reply(user_obj, text_content):
    """Kullanıcıya mesaj gönderir ve başarılıysa botun yanıtını da DB'ye kaydeder"""
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {'Authorization': 'Bearer IGAATI8zcb86NBZAFlDWmxCMC1kLVFJWWdkSFctS0ZAFYlcyS0xaSzVybGxxMUJIaFUtaUU5cGJpUHNxODRJdzhtVHpOZAjNqQVRjWVNUM3NfSTZAJX1laaHFNakIxT05ZAM19nSEdGM1JvZAk5JNHdicks0MXlGVzBjdERrSjg3R2h6WQZDZD',
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
        
