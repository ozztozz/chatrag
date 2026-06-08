import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from .models import UserAccount

# In production, move these safely to environment variables or settings.py
INSTAGRAM_APP_ID = '1568510561659920'
INSTAGRAM_APP_SECRET = 'ozztozzSecretKey'  # Replace with your actual Instagram App Secret
REDIRECT_URI = 'https://rinsing-postwar-excuse.ngrok-free.dev/auth/oauth/callback/' # Must exactly match Meta Dashboard

def login_page(request):
    """Renders the standard login template UI."""
    return render(request, 'login.html')

def instagram_login(request):
    """Redirects the user directly to Meta's login screen."""
    # Define what permissions your app is requesting (comma-separated)
    # For basic Consumer API: 'instagram_graph_user_profile,instagram_graph_user_media'
    # For Business Graph API: 'instagram_basic,instagram_manage_insights,pages_read_engagement'
    scopes = 'instagram_graph_user_profile,instagram_graph_user_media'
    
    instagram_auth_url = (
        f"https://api.instagram.com/oauth/authorize"
        f"?force_reauth=true"
        f"&client_id={INSTAGRAM_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=instagram_business_basic%2Cinstagram_business_manage_messages%2Cinstagram_business_manage_comments%2Cinstagram_business_content_publish%2Cinstagram_business_manage_insights"
        f"&response_type=code"
    )
    return redirect(instagram_auth_url)

def instagram_callback(request):
    """Instagram'ın kullanıcıyı geri gönderdiği ve kodu onaylattığımız yer."""
    code = request.GET.get('code')
    print("Instagram'dan gelen kod:", code)  # Debug için ekledik
    
    if not code:
        return JsonResponse({"error": "Code parametresi bulunamadı."}, status=400)
    
    # 2. META'YA GÖNDERİLEN VERİ PAKETİ
    token_url = "https://api.instagram.com/oauth/access_token"
    payload = {
        'client_id': INSTAGRAM_APP_ID,
        'client_secret': INSTAGRAM_APP_SECRET,
        'grant_type': 'authorization_code',
        # CRITICAL: Bu satırın varlığından ve REDIRECT_URI'ın yukarıdakiyle 
        # aynı olduğundan emin olun. Meta burayı kontrol ediyor.
        'redirect_uri': REDIRECT_URI, 
        'code': code
    }
    
    # Instagram'a doğrulama kodunu gönderip Access Token istiyoruz
    response = requests.post(token_url, data=payload)
    print("META DETAYLI CEVAP:", response.text)
    token_data = response.json()
    
    if 'access_token' in token_data:
        # Başarılı! Token'ı aldınız.
        access_token = token_data.get('access_token')
        user_id = token_data.get('user_id')
        user_obj, created = UserAccount.objects.get_or_create(instagram_user_id=user_id)
        user_obj.access_token = access_token
        user_obj.save()
        return JsonResponse({"status": "Başarılı!", "data": token_data})
    else:
        # Hata buraya düşüyor
        return JsonResponse({
            "error": "Token alınamadı", 
            "meta_response": token_data  # Meta'dan gelen tam hata mesajını görmek için
        }, status=400)
    
   