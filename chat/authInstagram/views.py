import logging
import secrets
from urllib.parse import urlencode

import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from .models import UserAccount

INSTAGRAM_APP_ID = settings.INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET = settings.INSTAGRAM_APP_SECRET
REDIRECT_URI = settings.INSTAGRAM_REDIRECT_URI
logger = logging.getLogger(__name__)

def login_page(request):
    """Renders the standard login template UI."""
    return render(request, 'login.html')

def instagram_login(request):
    """Redirects the user directly to Meta's login screen."""
    # Define what permissions your app is requesting (comma-separated)
    # For basic Consumer API: 'instagram_graph_user_profile,instagram_graph_user_media'
    # For Business Graph API: 'instagram_basic,instagram_manage_insights,pages_read_engagement'
    scopes = 'instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments,instagram_business_content_publish,instagram_business_manage_insights'
    state = secrets.token_urlsafe(32)
    request.session['instagram_oauth_state'] = state

    instagram_auth_url = 'https://api.instagram.com/oauth/authorize?' + urlencode({
        'force_reauth': 'true',
        'client_id': INSTAGRAM_APP_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': scopes,
        'response_type': 'code',
        'state': state,
    })
    return redirect(instagram_auth_url)

def instagram_callback(request):
    """Instagram'ın kullanıcıyı geri gönderdiği ve kodu onaylattığımız yer."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    expected_state = request.session.pop('instagram_oauth_state', None)

    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        return JsonResponse({"error": "Geçersiz OAuth state değeri."}, status=400)
    
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
    response = requests.post(token_url, data=payload, timeout=10)
    try:
        token_data = response.json()
    except ValueError:
        logger.error("Instagram token endpoint returned a non-JSON response", exc_info=True)
        return JsonResponse({"error": "Instagram doğrulaması başarısız."}, status=502)
    
    if 'access_token' in token_data:
        # Başarılı! Token'ı aldınız.
        access_token = token_data.get('access_token')
        user_id = token_data.get('user_id')
        user_obj, created = UserAccount.objects.get_or_create(instagram_user_id=user_id)
        user_obj.access_token = access_token
        user_obj.save()
        return JsonResponse({"status": "Başarılı!"})
    else:
        # Hata buraya düşüyor
        logger.warning("Instagram token exchange failed with status %s", response.status_code)
        return JsonResponse({"error": "Instagram doğrulaması başarısız."}, status=400)
    
   