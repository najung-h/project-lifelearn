# backend/apps/accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """
    UI 요구사항:
    - 아이디(username)
    - 비밀번호
    - 이름(name)
    - 이메일(email)
    - (이메일 인증 여부) #TODO :추후구현
    """
    first_name = None
    last_name = None
    name = models.CharField("이름", max_length=30)
    email = models.EmailField("이메일", unique=True)
    is_email_verified = models.BooleanField(default=False)  # TODO: 추후 이메일 인증 기능 구현 시 사용

    def __str__(self):
        return self.username


class EmailVerification(models.Model):
    """
    이메일 인증코드 저장 (회원가입 전)
    - code는 평문 저장 대신 해시 저장(간단 보안)
    """
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        indexes = [ 
            models.Index(fields=["email", "expires_at"]), 
        ] 
    
    @property 
    def is_expired(self) -> bool: 
        return timezone.now() > self.expires_at 
    
    @property 
    def is_verified(self) -> bool: 
        return self.verified_at is not None


class UserConsent(models.Model):
    """
    약관동의 저장
    UI 체크박스:
    - 서비스 이용약관(필수)
    - 개인정보 수집/이용(필수)
    - 마케팅 수신(선택)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="consent")
    terms_service = models.BooleanField(default=False)
    terms_privacy = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(default=False)

    agreed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} consent"
