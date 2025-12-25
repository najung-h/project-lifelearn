import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

class Command(BaseCommand):
    help = 'Setup Google SocialApp configuration from environment variables'

    def handle(self, *args, **options):
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        secret_key = os.environ.get('GOOGLE_SECRET_KEY')

        if not client_id or not secret_key:
            self.stdout.write(self.style.WARNING('GOOGLE_CLIENT_ID or GOOGLE_SECRET_KEY not found in environment variables.'))
            return

        # 1. Site 설정 (ID=1 기본 사이트)
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={'domain': 'localhost', 'name': 'localhost'}
        )
        if not created and (site.domain != 'localhost' or site.name != 'localhost'):
            site.domain = 'localhost'
            site.name = 'localhost'
            site.save()

        # 2. SocialApp 설정
        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google Login',
                'client_id': client_id,
                'secret': secret_key,
            }
        )
        
        # Site 연결 확인
        if not app.sites.filter(id=site.id).exists():
            app.sites.add(site)

        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created SocialApp: {app.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated SocialApp: {app.name}'))
