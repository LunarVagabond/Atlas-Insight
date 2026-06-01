from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the GitHub SocialApp DB record so admin shows it linked to social accounts.'

    def handle(self, *args, **options):
        from allauth.socialaccount.models import SocialApp

        app_cfg = settings.SOCIALACCOUNT_PROVIDERS.get('github', {}).get('APP', {})
        client_id = app_cfg.get('client_id', '') or ''
        secret = app_cfg.get('secret', '') or ''

        if not client_id:
            self.stderr.write(self.style.ERROR(
                'GITHUB_CLIENT_ID not set in .env — aborting. '
                'A SocialApp with empty credentials would break OAuth. '
                'Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET then re-run.'
            ))
            return

        app, created = SocialApp.objects.update_or_create(
            provider='github',
            defaults={
                'name': 'GitHub',
                'client_id': client_id,
                'secret': secret,
            },
        )
        site = Site.objects.get_current()
        app.sites.add(site)
        status = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(f'GitHub SocialApp {status} (id={app.pk}, site={site.domain})'))
