import hashlib
import hmac
import json
import logging
import time
from google import genai
from google.genai import errors  # Yeni SDK için doğru hata yönetimi
import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import InstagramUser, InstagramMessage, MessageJob
from google.genai import types
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from authInstagram.models import UserAccount


logger = logging.getLogger(__name__)


class InstagramTokenError(Exception):
    """Raised when Meta rejects the access token."""



GEMINI_API_KEY = settings.GEMINI_API_KEY


def has_valid_meta_signature(request):
    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    if not signature.startswith('sha256=') or not settings.INSTAGRAM_APP_SECRET:
        return False

    expected_signature = 'sha256=' + hmac.new(
        settings.INSTAGRAM_APP_SECRET.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


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

def get_gemini_messages(user_obj, new_message, limit=30, additional_instruction=''):
    name = user_obj.name if user_obj.name else "Değerli Velimiz"

    # 1. Kullanıcıya hitap etme kuralını ekliyoruz
    name_part = f"\n\n[Kullanıcı Bilgisi]\nKullanıcının adı {name.title()}. Konuşmaya başlarken kullanıcıya ismiyle hitap et ve samimi/profesyonel bir dil kullan."

    # 2. Bilgi tabanını net bir şekilde etiketleyerek ayırıyoruz (XML Etiketleri ile)
    knowledge_part = f"\n\n[Bilgi Tabanı]\nAşağıdaki <knowledge_base> etiketleri içindeki verilere kesinlikle sadık kal. Buradaki bilgiler dışına çıkma:\n<knowledge_base>\n{KNOWLEDGE}\n</knowledge_base>"

    # 3. Hepsini ana PROMT değişkeninizle birleştiriyoruz
    final_system_instruction = PROMT + name_part + knowledge_part
    if additional_instruction:
        final_system_instruction += f"\n\n[Aktif Akış Adımı]\n{additional_instruction}"

    old_messages_data = get_old_messages(user_obj, limit=limit)

    client = genai.Client(api_key=GEMINI_API_KEY)

    for model in settings.GEMINI_MODELS:
        chat = client.chats.create(
            model=model,
            history=old_messages_data,
            config=types.GenerateContentConfig(
                system_instruction=final_system_instruction,
                temperature=0.3
            )
        )

        for attempt in range(3):
            try:
                response = chat.send_message(new_message)
                if response and getattr(response, 'text', None):
                    return response.text

                logger.warning("Gemini model %s returned an empty response on attempt %s", model, attempt + 1)
            except errors.APIError as error:
                logger.error(
                    "Gemini model %s failed on attempt %s (code=%s)",
                    model,
                    attempt + 1,
                    error.code,
                    exc_info=True,
                )
            except Exception:
                logger.exception("Unexpected Gemini error for model %s on attempt %s", model, attempt + 1)

            if attempt < 2:
                time.sleep((attempt + 1) * 3)

    logger.error("All configured Gemini models failed")
    return None

def get_instagram_user_info(instagram_id, access_token):
    url = f"https://graph.instagram.com/v25.0/{instagram_id}"
    response = requests.get(
        url,
        params={
            "fields": "name,username,is_user_follow_business",
            "access_token": access_token,
        },
        timeout=10,
    )
    metadata = response.json()
    if response.status_code in (401, 403) or metadata.get('error', {}).get('code') in (190, 463, 467):
        raise InstagramTokenError('Instagram access token was rejected')
    response.raise_for_status()
    return metadata

def send_writing_indicator(sender_id, access_token):
    """Instagram'a yazıyor göstergesi gönderir"""
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        "recipient": {"id": sender_id},
        "sender_action": "typing_on"
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code in (401, 403):
        raise InstagramTokenError('Instagram access token was rejected')
@csrf_exempt
def instagram_webhook(request):
    # 1. DOĞRULAMA ADIMI (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.INSTAGRAM_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Doğrulama başarısız", status=403)

    # 2. VERİ ALMA VE KAYDETME ADIMI (POST)
    elif request.method == 'POST':
        if not has_valid_meta_signature(request):
            return HttpResponse("Geçersiz webhook imzası", status=403)

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
                        recipient_id = messaging_event.get('recipient', {}).get('id')
                        entry_account_id = entry.get('id')

                        # 1. Kural: Mesaj metni var mı ve botun kendi mesajı (echo) değil mi?
                        if message_id and message_text and not message_data.get('is_echo'):
                            account = UserAccount.objects.filter(
                                instagram_user_id__in=[recipient_id, entry_account_id]
                            ).first()
                            if not account:
                                logger.warning(
                                    "Ignoring message %s for unconnected Instagram account %s",
                                    message_id,
                                    recipient_id,
                                )
                                continue

                            # KULLANICIYI KAYDET (Yoksa oluşturur, varsa mevcut olanı getirir)
                            user_obj, created = InstagramUser.objects.get_or_create(instagram_id=sender_id)
                            incoming_message, created = InstagramMessage.objects.get_or_create(
                                message_id=message_id,
                                defaults={
                                    'user': user_obj,
                                    'account': account,
                                    'text': message_text,
                                    'is_from_user': True,
                                },
                            )
                            if not created and incoming_message.account_id is None:
                                incoming_message.account = account
                                incoming_message.save(update_fields=['account'])
                            if created or incoming_message.account_id == account.id:
                                MessageJob.objects.get_or_create(message=incoming_message)

        return HttpResponse("EVENT_RECEIVED", status=200)

    return HttpResponse("Yöntem Desteklenmiyor", status=405)



import re


def send_and_save_reply(user_obj, gemini_response, access_token):
    url = "https://graph.instagram.com/v25.0/me/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
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
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response_data = response.json()

        if response.status_code in (401, 403) or response_data.get('error', {}).get('code') in (190, 463, 467):
            raise InstagramTokenError('Instagram access token was rejected')

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
            logger.warning("Meta API rejected message with status %s", response.status_code)
            return False

    except requests.exceptions.RequestException as e:
        logger.exception("Meta API connection error")
        return False