# backend/apps/accounts/views.py

from django.shortcuts import render
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    # TODO: 프론트엔드 URL로 변경 필요
    # dj-rest-auth의 기본 동작상 access_token만으로 처리되므로 필수 항목은 아님.
    # TODO: console.cloud.google.com/에 일치하게 등록해두었는지 확인 필요
    callback_url = "http://localhost/api/v1/accounts/google/login/callback/" 
    