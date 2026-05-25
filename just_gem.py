import os
import time
from google import genai
from google.genai.errors import APIError
import os
from dotenv import load_dotenv
# 1. Adım: İstemciyi başlatın

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 2. Adım: 200 Satırlık Sabit Bilgi Tabanınız
with open("alpha_chat.txt", "r", encoding="utf-8") as f:
    data = f.read()
bilgi_tabani =data


# 3. Adım: Her kullanıcının hafızasını tutacak boş bir sözlük
# Bu sözlük arka planda şöyle görünecek: {"user_123": sohbet_objesi, "user_456": sohbet_objesi}
aktif_sohbetler = {}

# 4. Adım: Kullanıcıya göre sohbeti getiren veya yeni oluşturan fonksiyon
def kullanici_sohbetini_getir(user_id):
    # Eğer bu kullanıcı ilk defa yazıyorsa, ona özel yeni bir hafıza (oturum) oluştur
    if user_id not in aktif_sohbetler:
        print(f"🔄 {user_id} için yeni bir sohbet oturumu başlatıldı.")
        
        yeni_chat = client.chats.create(
            model="gemini-2.5-flash",
            config={
                "system_instruction": f"Sen sadece bu verilere göre cevap veren bir asistansın:\n{bilgi_tabani}"
            }
        )
        # Oluşturulan bu özel oturumu kullanıcının ID'sine kaydet
        aktif_sohbetler[user_id] = yeni_chat
        
    return aktif_sohbetler[user_id]

# 5. Adım: Mesaj Gönderme Fonksiyonu (Hata Kontrollü)
def mesaji_yanitla(user_id, mesaj):
    try:
        # Kullanıcının kendi özel hafıza nesnesini al
        kullanici_sohbeti = kullanici_sohbetini_getir(user_id)
        
        # Sadece o kullanıcının geçmişi üzerinden mesajı gönder
        response = kullanici_sohbeti.send_message(mesaj)
        return response.text
        
    except APIError as e:
        if e.code == 429 or "ResourceExhausted" in str(e):
            return "⚠️ Şu an çok yoğunum (Dakikalık ücretsiz kota doldu). Lütfen 30 saniye sonra tekrar deneyin."
        return f"❌ Bir hata oluştu: {e}"

# --- SİMÜLASYON (Farklı kişilerin yazdığını varsayalım) ---

# 1. Senaryo: Ahmet sisteme giriyor
print("Bot:", mesaji_yanitla("ahmet_123", "Merhaba, 7 yasinda kizim var. Hangi sporları önerirsiniz?"))

# 2. Senaryo: Mehmet sisteme giriyor (Ahmet'ten tamamen bağımsız)
print("Bot:", mesaji_yanitla("mehmet_555", "Selam, ben Mehmet. tesisleriniz nerede"))

# 3. Senaryo: Ahmet geri dönüp adını soruyor (Sistem Ahmet'i hatırlıyor)
print("Bot:", mesaji_yanitla("ahmet_123", "yas gruplari neler?")) 
# Çıktı: "Senin adın Ahmet." olur, Mehmet'in sorduğu Ürün A ile karışmaz.
