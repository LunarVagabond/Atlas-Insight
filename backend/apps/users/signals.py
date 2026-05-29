from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.dispatch import receiver


def _sync_github_fields(sociallogin, **kwargs):
    if sociallogin.account.provider != 'github':
        return
    user = sociallogin.user
    extra = sociallogin.account.extra_data or {}
    user.github_login = extra.get('login', '') or user.username
    user.avatar_url = extra.get('avatar_url', '')
    user.save(update_fields=['github_login', 'avatar_url'])


@receiver(social_account_added)
def on_social_added(sender, request, sociallogin, **kwargs):
    _sync_github_fields(sociallogin)


@receiver(social_account_updated)
def on_social_updated(sender, request, sociallogin, **kwargs):
    _sync_github_fields(sociallogin)
