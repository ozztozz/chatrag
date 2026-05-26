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
    data="""
    ANA VİZYON
    Alpha Academy klasik bir yüzme kursu değildir. Biz sporcularımıza yalnızca teknik eğitim veren bir yapı değil; disiplin, özgüven ve sporcu karakteri kazandıran kaliteli bir spor kulübüyüz.

    Kalabalık sistem yerine sınırlı sayıda sporcuyla çalışırız. Her sporcunun gelişimi birebir takip edilir. Sporcularımız kalabalıkta kaybolmaz.

    Önceliğimiz madalya değil, iyi sporcu yetiştirmektir. Disiplin ve doğru teknik gelişim sağlandığında başarı zaten doğal bir sonuç olarak gelir.
    Tüm eğitim kadromuz BESYO (Beden Eğitimi ve Spor Yüksekokulu) mezunu, pedagojik formasyon sahibi ve branşında deneyimli antrenörlerden oluşur. Sporcularımız, sadece bir eğitmenle değil, sporu akademik ve teknik açıdan özümsemiş profesyonellerle yol alır.
    ||
    FİYAT BİLGİSİ
    Fiyatlarımız, sporcumuzun seviyesine ve haftalık antrenman programına göre belirlenmektedir. En sağlıklı bilgiyi ön görüşme ve seviye tespiti sonrası paylaşıyoruz.
    ||
    KARŞILAMA MESAJI
    “Merhaba 😊
    Alpha Academy Spor Kulübü’ne hoş geldiniz. Ben yapay zeka yardımcınızım.

    Size nasıl yardımcı olabilirim?”
    ||
    YAŞ GRUBU KURALLARI:
    [3-6 Yaş]: Odak: Güven ve oyun. Ton: Sabırlı. Mesaj: Zorlama yok, su korkusunu yenme.  
    [7-12 Yaş]: Odak: Teknik ve disiplin. Ton: Profesyonel. Mesaj: Birebir takip, kalabalıkta kaybolmama.  
    [13+ Yaş]: Odak: Performans ve Milli Takım. Ton: Hedef odaklı. Mesaj: Profesyonel kariyer planlaması. 
    ||
    3-6 YAŞ MESAJI

    1. Su Geçmişini Sorgulama Stratejisi
    "3-6 yaş grubu bizim için çok kıymetli! 🌟 Çocuklarımızın suyla kuracağı ilk bağın sevgi dolu olması önemlidir. Bu yaş grubunda önceliğimiz; çocuklarımızın suyu sevmesi, güven kazanması ve temel koordinasyon gelişimidir. Daha önce herhangi bir havuz deneyimi oldu mu? (Örneğin: suyu çok mu seviyor?)"
    2. Gelen Yanıta Göre Yaklaşım
        Eğer su deneyimi varsa, korku yoksa, cevap olumlu bir içerikse : "Harika! Mevcut özgüvenini, profesyonel antrenörlerimizin akademik yaklaşımıyla doğru tekniğe dönüştürebiliriz."
        Eğer korkuyorsa, olumsuz ifadeler varsa: "Bu çok doğal bir durum 😊 Biz çocuklarımızı asla zorlamıyoruz. Oyun ve güven odaklı, kademeli bir alışma yöntemi uyguluyoruz." 

    3. Randevu Önerisi ve Davet Formülasyonu
    Su geçmişini öğrendikten sonra, konuyu kulübün en güçlü olduğu "yüz yüze iletişim" noktasına bağlamalısın:

    "Sizin için en doğru kulübü seçmenin önemli bir karar olduğunu biliyoruz 😊 Bu yüzden tesisimizi ve antrenman disiplinimizi yerinde görmenizi çok önemsiyoruz. Sizi kulübümüzde ağırladığımızda, antrenörlerimiz eşliğinde sporcu adayımız için ücretsiz bir seviye tespiti yapıyoruz. Milli takım sporcularımızın yetiştiği bu atmosferi beraber solumaya ne dersiniz? "
    ||
    7-12 YAŞ MESAJI
    1. Su Geçmişini Sorgulama Stratejisi
    “Bu yaş aralığı teknik gelişim, spor disiplini kazanımı ve ve sporcu karakterinin oluşumu açısından çok değerlidir.Sporcu adayımızın daha önce yüzme geçmişi var mıdır? Varsa kısa şekilde bizimle paylaşabilir misiniz 😊
    2. Gelen Yanıta Göre Yaklaşım
            Eğer korkuyorsa, olumsuz ifadeler varsa: "Bu çok doğal bir durum 😊 Biz çocuklarımızı asla zorlamıyoruz. Güven odaklı, kademeli bir alışma yöntemi uyguluyoruz." 
        Eğer sporcu geçmişi yoksa: "Spora başlamak, antrenman , sporcu karakteri kazanmak için doğru bir yaştasınız. Kulübümüzün kursiyer gruplarına başlayarak spor hayatınıza birlikte başlayabiliriz"
        Eğer sporcu geçmişi varsa ve olumlu ifadeler kullandıysa :""Harika! Mevcut altaypısını profesyonel antrenörlerimizin akademik yaklaşımıyla ileriye taşıyarak lisanslı yarış grubumuza katılabilirsiniz."

    3. Randevu Önerisi ve Davet Formülasyonu
    Alpha Academy’de sporcularımız kalabalık gruplarda kaybolmaz. Antrenörlerimiz her öğrenciyi birebir takip eder.

    Amacımız sadece yüzme öğretmek değil; iyi sporcu karakteri oluşturmaktır. Bu yüzden tesisimizi ve antrenman disiplinimizi yerinde görmenizi çok önemsiyoruz. Sizi kulübümüzde ağırladığımızda, antrenörlerimiz eşliğinde sporcu adayımız için ücretsiz bir seviye tespiti yapıyoruz. Milli takım sporcularımızın yetiştiği bu atmosferi beraber solumaya ne dersiniz?”
    ||
    13+ YAŞ MESAJI
    “Bu yaş grubunda teknik gelişim kadar performans planlaması da önemlidir.

    Sporcularımıza seviyelerine göre özel gelişim takibi uygulanır. Disiplini ve devamlılığı sağlayan sporcularımız için yarışma ve milli takım hedefleri ulaşılabilir hale gelir.”
    ||
    YETİŞKİN GRUBU MESAJI

    Bu yaş gruplarımıza ek olarak 😊

    20 yaş ve üzeri yetişkin gruplarımız da bulunmaktadır 🏊‍♂️

    Yetişkin sporcularımız için;
    ▪️ başlangıç seviyesi,
    ▪️ teknik gelişim,
    ▪️ kondisyon amaçlı,
    ▪️ özel gelişim odaklı

    antrenman planlamaları yapılmaktadır.

    Detaylı bilgi ve uygun saat planlaması için iletişim numaranızı paylaşabilir misiniz? 😊
    ||
    SORU:
    “Çocuğum sudan korkuyor.”

    CEVAP:
    “Bu çok doğal bir durum 😊

    Çocuklarımızı kesinlikle zorlayarak değil; oyun, güven ve kademeli alışma yöntemiyle suya adapte ediyoruz.

    Amacımız önce çocuğun suyu sevmesi ve kendini güvende hissetmesidir.”
    ||
    SORU:
    “Kaç kişilik gruplar?”

    CEVAP:
    “Biz büyük kulüplerdeki kalabalık sistemin aksine kaliteli eğitim modeliyle çalışıyoruz.

    Her kulvarda sınırlı sayıda sporcu bulunur. Bu sayede antrenörlerimiz her öğrenciyi birebir takip eder.”
    ||
    SORU:
    “Ne kadar sürede öğrenir?”

    CEVAP:
    “Her bireyin gelişim süreci farklıdır 😊

    Genellikle başlangıç seviyesinde 8-12 ders sonunda temel koordinasyon gelişimi görülür.

    Ancak önceliğimiz hızlı öğrenme değil; doğru teknik ve kalıcı gelişimdir.”
    ||
    SORU:
    “Madalya garantisi var mı?”

    CEVAP:
    “Bizim önceliğimiz madalya değil, sporcu karakteridir.

    Doğru disiplin ve düzenli gelişim sağlandığında başarı zaten doğal olarak gelir.”
    ||
    SORU:
    “Yeni kulüpsünüz, neden sizi seçelim?”

    CEVAP:
    “Kulübümüz genç bir yapı olmasına rağmen milli takım seviyesine sporcu yetiştirerek sistemini kanıtlamıştır.
    kaliteli yapımız sayesinde her sporcuya özel gelişim alanı sunabiliyoruz.
    Sadece yüzme bilenleri değil, yüzme eğitiminin akademik altyapısına sahip profesyonelleri bir araya getirdik."
    ||
    SORU:
    “Hijyen ve güvenlik nasıl?”

    CEVAP:
    “Sağlık ve güvenlik bizim için önceliklidir.

    Havuzumuzun hijyen değerleri düzenli olarak kontrol edilmekte ve periyodik analizlerden geçmektedir.

    kaliteli yapımız sayesinde yoğunluk kontrollü ilerlemektedir.”
    ||
    SORU: "Çocuğum ilk derslerde ağlarsa ya da girmek istemezse yaklaşımınız ne oluyor?"

    CEVAP: "Bunu çok doğal bir adaptasyon süreci olarak görüyoruz. Asla zorlamıyoruz. Antrenörlerimiz, sporcumuzun hızına saygı duyarak, süreci oyunla ve sabırla yönetiyor. Alpha Academy'de başarı, havuzun kenarında güvenle gülümsemekle başlar."
    ||
    SORU:
    “Antrenörlerinizin tecrübesi nedir? Çocuğumla kim ilgilenecek?”

    CEVAP:
    “Alpha Academy’de sporcularımız emin ellerde 😊

    Eğitim kadromuzun tamamı BESYO mezunu, alanında uzman ve çocuk psikolojisi/pedagojisi konusunda deneyimli antrenörlerden oluşmaktadır. Bizim için sadece teknik öğretmek değil, sporcunun gelişim evrelerini bilerek doğru müdahalede bulunmak esastır. Her antrenörümüz, sorumlu olduğu sporcunun gelişimini akademik bir titizlikle takip eder.
    ||
    SOSYAL ORTAM MESAJI
    “Alpha Academy’de hiçbir çocuk yalnız hissetmez.
    Yeni gelen sporcular takım arkadaşı olarak karşılanır. Çocuklarımızın birbirini desteklediği güvenli ve aile sıcaklığında bir ortam oluşturuyoruz.”
    ||
    İLETİŞİM
    "Bizimle iletişim kurmak isterseniz 05064802024 numaralı telefondan arayabilir ya da mesaj atabilirsiniz. Size en kısa sürede dönüş sağlayarak, merak ettiğiniz tüm konularda bilgi verebiliriz."
    ||
    RANDEVU DAVETİ
    “Sizin için en doğru kulübü seçmenin önemli bir karar olduğunun farkındayız 😊
    Bu yüzden tesisimizi, antrenman disiplinimizi ve kaliteli yapımızı yerinde görmenizi çok önemsiyoruz.
    Antrenörlerimiz eşliğinde sporcu adayımız için ücretsiz bir seviye tespiti yapıyor ve gelişimine nereden başlamamız gerektiğini birlikte planlıyoruz.”
    Deneme dersinizi aşağıdaki gün ve saatlerde planlayabiliriz:
        📍 * İncek-Alacaatlı Tesisimiz:
        Blue Çarşı, Alacaatlı Mahallesi, Çankaya/Ankara.
        Tesisimize Ulaşın:https://maps.app.goo.gl/Nf7YfHe63v1ZyMEA8
        Çarşamba, Cuma
        🕕 18.00 – 19.00
        Cumartesi, Pazar
        🕘 09.00 – 10.00
        🕐 13.00 – 14.00
        📍 Eryaman Tesisimiz
        Cumartesi, Pazar
        🕑 14.00 – 15.00
        🕒 15.00 – 16.00
        
    Size uygun gün ve saat bilgisini iletmeniz durumunda deneme ders planlamanızı oluşturalım 😊🏊‍♂️
    ||
    KAPANIŞ MESAJI
    “Alpha Academy’de çocuklarımız yalnızca yüzme öğrenmez; disiplin, özgüven ve sporcu karakteri kazanır.

    Milli takım vizyonuyla ilerleyen bu atmosferi yerinde görmeniz için sizi kulübümüzde ağırlamaktan mutluluk duyarız 😊”
    ||
    RANDEVU BİLGİ TOPLAMA
    “Size uygun bir görüşme planlayabilmemiz için aşağıdaki bilgileri paylaşabilir misiniz?
    Veli Ad Soyad  Sporcu Yaşı İletişim Numaranız
    Tercih edilen lokasyon 
    İncek-Alacatlı Blue Çarşı, Alacaatlı Mahallesi Simpaş İncek Çankaya/Ankara  
    Eryaman ”
    Bilgi Notu: "İlk buluşmamız için yanınızda; mayo/şort, bone, gözlük, terlik ve havlu getirmeniz yeterlidir. Sizi heyecanla bekliyoruz! 😊"
"""
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
    prompt = """
Sen Alpha Academy Spor Kulübü’nün profesyonel, samimi ve güven veren temsilcisisin. 
Bot olduğunu belirt. 
Amacın, velileri bilgilendirmek ve onları yüz yüze görüşme için tesise davet etmektir. 
Kullanıcı telefon numaramızı isterse teşekkür edip sohbeti sonlandır. 
Randevuyu kabul ederse Sporcu ve veli adını iste.
Kullanıcının sorularını verilen içerik bilgisine dayalı olarak yanıtla.
Kullanıcı telefon numaramızı isterse teşekkür edip sohbeti sonlandır. Bilgi isteme
randevu gününü kaydet
sporcu yaşını kaydet
sporcu ve veli adını kaydet
telefonu kaydet

"""
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
        
