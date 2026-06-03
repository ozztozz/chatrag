import json
import time
from google import genai
from google.genai import errors  # Yeni SDK için doğru hata yönetimi
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import InstagramUser, InstagramMessage
from google.genai import types
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings



GEMINI_API_KEY = settings.GEMINI_API_KEY
INSTAGRAM_ACCESS_TOKEN = settings.INSTAGRAM_ACCESS_TOKEN.strip()


with staticfiles_storage.open('knowledge.txt') as f:
        KNOWLEDGE = f.read().decode('utf-8')
with staticfiles_storage.open('promt.txt') as f:
        PROMT = f.read().decode('utf-8')

def get_old_messages(user_obj, limit=30):
    eski_mesajlar = []
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

def get_gemini_messages(user_obj, new_message, limit=30):
    name = user_obj.name if user_obj.name else "Değerli Velimiz"

    # 1. Kullanıcıya hitap etme kuralını ekliyoruz
    name_part = f"\n\n[Kullanıcı Bilgisi]\nKullanıcının adı {name.title()}. Konuşmaya başlarken kullanıcıya ismiyle hitap et ve samimi/profesyonel bir dil kullan."

    # 2. Bilgi tabanını net bir şekilde etiketleyerek ayırıyoruz (XML Etiketleri ile)
    knowledge_part = f"\n\n[Bilgi Tabanı]\nAşağıdaki <knowledge_base> etiketleri içindeki verilere kesinlikle sadık kal. Buradaki bilgiler dışına çıkma:\n<knowledge_base>\n{KNOWLEDGE}\n</knowledge_base>"

    # 3. Hepsini ana PROMT değişkeninizle birleştiriyoruz
    final_system_instruction = PROMT + name_part + knowledge_part

    old_messages_data = get_old_messages(user_obj, limit=limit)

    client = genai.Client(api_key=GEMINI_API_KEY)

    chat = client.chats.create(
        model="gemini-2.5-flash-lite",
        history=old_messages_data,
        config=types.GenerateContentConfig(
            system_instruction=final_system_instruction,
            temperature=0.3
        )
    )

    response = None
    for i in range(3):  # 3 deneme hakkı
        try:
            response = chat.send_message(new_message)

            # Başarılı bir response aldık mı ve içinde text var mı? (Güvenlik filtresi kontrolü)
            if response and getattr(response, 'text', None):
                return response.text
            else:
                # Response döndü ama text yoksa (örn: Safety Block / Güvenlik engeli)
                print(f"Deneme {i+1}: Boş veya filtrelenmiş yanıt alındı.")
                chat.rewind()  # Boş turn'ü geçmişten silerek chat'i temiz tutuyoruz.

        except errors.APIError as e:
            # API tabanlı hatalar (Kota aşımı, 500 server hatası vb.)
            print(f"Deneme {i+1} - Gemini API Hatası ({e.code}): {e.message}")
            try:
                chat.rewind()  # Hata alan mesajı geçmişten geri al
            except Exception:
                pass

            if i == 2:  # Son denemede de başarısız olduysa
                return f"Error: {e.code} - {e.message}"

        except Exception as e:
            # Diğer beklenmedik sistem/bağlantı hataları
            print(f"Deneme {i+1} - Beklenmeyen hata: {e}")
            try:
                chat.rewind()
            except Exception:
                pass

            if i == 2:
                return "Üzgünüm, şu anda yanıt veremiyorum. (Sistem hatası)"

        # Yeniden denemeden önce bekle (Exponential backoff mantığı: her adımda daha çok bekle)
        time.sleep((i + 1) * 3)

    # Döngü bitti ama yukarıdaki return'lere takılmadıysa (Nadir bir case)
    return "Üzgünüm, şu anda yanıt veremiyorum."

def get_instagram_user_info(instagram_id):
    url = f"https://graph.instagram.com/v25.0/{instagram_id}?fields=name,username,is_user_follow_business&access_token=IGAATI8zcb86NBZAGFZAYVhSNExKb19IeE1tMmhBMU9uRU5WWWIzOUctVVRJWVByLTdLMEFHRGFBMjYyZA1l3Y0hKa3cxTkZAKWTB6V1laWkQ5UDZAmUUNKdHcwc29yb3pvZAVpxSmk1eWFKaG50WGhFZA1VIMGhkN1B5cThWcFdHTDU3WQZDZD"
    response=requests.get(url)
    metadata=response.json()
    return metadata

def send_writing_indicator(sender_id):
    """Instagram'a yazıyor göstergesi gönderir"""
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {
        'Authorization': 'Bearer IGAATI8zcb86NBZAGE5R3IzNWpPc3pWbnE4aFBLSzM5NE5XdDhtWDRpSnNHRDYzUmJ0YUtRYjRIRzNnc1BXTnRMRlpSOGMxalJGck9LUktCV1ZAPcVFNWjhlY3dxS3VRWGlTejZASaEZA1aktCM1BCMldxUjQ2NlZAjVTRxM3puRUNZASQZDZD',
        'Content-Type': 'application/json'
    }
    payload = {
        "recipient": {"id": sender_id},
        "sender_action": "typing_on"
    }
    response=requests.post(url,headers=headers,json=payload)
@csrf_exempt
def instagram_webhook(request):
    # 1. DOĞRULAMA ADIMI (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == 'fkalpha_academy_token' :
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
                        recipient_id = messaging_event['recipient']['id']

                        # 1. Kural: Mesaj metni var mı ve botun kendi mesajı (echo) değil mi?
                        if message_text and not message_data.get('is_echo'):

                            # KULLANICIYI KAYDET (Yoksa oluşturur, varsa mevcut olanı getirir)
                            user_obj, created = InstagramUser.objects.get_or_create(instagram_id=sender_id)
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


                            # GELEN MESAJI KAYDET (Aynı message_id daha önce işlenmediyse)
                            if not InstagramMessage.objects.filter(message_id=message_id).exists():
                                send_writing_indicator(sender_id)
                                # OTO YANIT METNİ
                                reply_text = get_gemini_messages(user_obj, message_text)
                                #reply_text = "Bu bir otomatik yanıttır. Mesajınız bize ulaştı ve en kısa sürede cevaplanacaktır."
                                InstagramMessage.objects.create(
                                    user=user_obj,
                                    message_id=message_id,
                                    text=message_text,
                                    is_from_user=True
                                )

                                # API Üzerinden Yanıt Gönder ve Gönderilen Yanıtı da Veritabanına Yaz
                                send_and_save_reply(user_obj, reply_text)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Yöntem Desteklenmiyor", status=405)



import re


def send_and_save_reply(user_obj, gemini_response):
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {
        'Authorization': 'Bearer IGAATI8zcb86NBZAGE5R3IzNWpPc3pWbnE4aFBLSzM5NE5XdDhtWDRpSnNHRDYzUmJ0YUtRYjRIRzNnc1BXTnRMRlpSOGMxalJGck9LUktCV1ZAPcVFNWjhlY3dxS3VRWGlTejZASaEZA1aktCM1BCMldxUjQ2NlZAjVTRxM3puRUNZASQZDZD',
        'Content-Type': 'application/json'
    }

    payload = {
        "recipient": {"id": user_obj.instagram_id}
    }

    # Adım 1: Yanıtın içindeki ilk '{' ve son '}' karakterlerini bulup sadece JSON kısmını izole edelim
    # Bu sayede başında/sonunda yazı veya görünmez karakterler olsa bile kod patlamaz.
    json_match = re.search(r'\{.*\}', gemini_response, re.DOTALL)

    is_json = False
    db_text = gemini_response

    if json_match:
        try:
            # Sadece eşleşen JSON string'ini alıyoruz
            pure_json_str = json_match.group(0)
            parsed_data = json.loads(pure_json_str)

            # Adım 2: Meta API'nin tam olarak beklediği 'message' yapısını hiyerarşik olarak bulalım
            # Eğer en dışta "message" anahtarı varsa onu soyuyoruz
            if "message" in parsed_data:
                message_content = parsed_data["message"]
            else:
                message_content = parsed_data

            # Adım 3: Eğer gerçekten bir attachment (buton şablonu) içeriyorsa payload'a ekle
            # send_and_save_reply fonksiyonunun içindeki if json_match bloğunun altı:
            if "attachment" in message_content:
                # Güvenlik Filtresi: Instagram'ın reddettiği phone_number butonunu temizle veya url'e çevir
                buttons = message_content.get("attachment", {}).get("payload", {}).get("buttons", [])
                for btn in buttons:
                    if btn.get("type") == "phone_number":
                        # Hataya sebep olan phone_number'ı Instagram'ın sevdiği wa.me linkine dönüştürüyoruz
                        btn["type"] = "web_url"
                        btn["url"] = f"https://wa.me/{btn.get('payload', '905064802024').replace('+', '')}"
                        btn.pop("payload", None) # payload alanını siliyoruz
                        btn["title"] = "Bizi Arayın 📞"

                payload["message"] = message_content
                db_text = message_content.get("attachment", {}).get("payload", {}).get("text", "[Konum Şablonu]")
                is_json = True
        except json.JSONDecodeError:
            # JSON dönüştürme başarısız olursa düz metin moduna geri düşer
            is_json = False

    # Eğer JSON şablonu değilse veya ayrıştırma başarısız olduysa düz metin olarak paketle
    if not is_json:
        payload["message"] = {"text": gemini_response}
        db_text = gemini_response

    # Adım 4: Meta API'ye Gönderim ve Veritabanı Kaydı
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()

        if "message_id" in response_data:
            InstagramMessage.objects.create(
                user=user_obj,
                message_id=response_data["message_id"],
                text=db_text,
                is_from_user=False
            )
            return True
        else:
            # Meta'dan dönen hatayı loglayın (Buton kısıtlamalarına takılıp takılmadığını görmek için)
            print(f"Meta API Reddedildi: {response_data}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Meta API Bağlantı Hatası: {e}")
        return False