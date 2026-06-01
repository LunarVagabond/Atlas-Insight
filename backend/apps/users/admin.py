from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from allauth.socialaccount.admin import SocialAppAdmin, SocialTokenAdmin
from allauth.socialaccount.models import SocialApp, SocialToken

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'github_login', 'email', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'github_login', 'email')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('GitHub', {'fields': ('github_login', 'avatar_url')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('GitHub', {'fields': ('github_login', 'avatar_url')}),
    )


class MaskedSocialAppForm(forms.ModelForm):
    class Meta:
        model = SocialApp
        exclude: list[str] = []
        widgets = {
            'client_id': forms.TextInput(attrs={'size': '100'}),
            'key': forms.TextInput(attrs={'size': '100'}),
            'secret': forms.PasswordInput(render_value=True, attrs={'size': '100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from allauth.socialaccount import providers
        self.fields['provider'] = forms.ChoiceField(choices=providers.registry.as_choices())


admin.site.unregister(SocialApp)

@admin.register(SocialApp)
class MaskedSocialAppAdmin(SocialAppAdmin):
    form = MaskedSocialAppForm


class MaskedSocialTokenForm(forms.ModelForm):
    class Meta:
        model = SocialToken
        exclude: list[str] = []
        widgets = {
            'token': forms.PasswordInput(render_value=True),
            'token_secret': forms.PasswordInput(render_value=True),
        }


admin.site.unregister(SocialToken)

@admin.register(SocialToken)
class MaskedSocialTokenAdmin(SocialTokenAdmin):
    form = MaskedSocialTokenForm
    list_display = ('app', 'account', 'masked_token', 'expires_at')

    def masked_token(self, token) -> str:
        t = token.token
        if not t:
            return '(empty)'
        return f'{t[:4]}{"•" * 20}'

    masked_token.short_description = 'Token'
