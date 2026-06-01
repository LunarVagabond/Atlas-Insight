import logging
import secrets
import uuid
from typing import Optional

from django.contrib.auth import logout as auth_logout
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer

from .models import APIToken

logger = logging.getLogger(__name__)
router = Router(tags=['auth'])


class APITokenAuth(HttpBearer):
    def authenticate(self, request, token: str):
        token_hash = APIToken.hash_token(token)
        try:
            api_token = APIToken.objects.select_related('user').get(
                token_hash=token_hash,
                revoked_at__isnull=True,
            )
        except APIToken.DoesNotExist:
            return None
        api_token.last_used_at = timezone.now()
        api_token.save(update_fields=['last_used_at'])
        request.api_token_user = api_token.user
        return api_token.user


api_token_auth = APITokenAuth()


class UserSchema(Schema):
    id: int
    username: str
    email: str
    github_login: str
    avatar_url: str
    github_connected: bool
    is_staff: bool
    is_superuser: bool


@router.get('/me', response={200: UserSchema, 401: dict})
def me(request):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    from allauth.socialaccount.models import SocialToken
    has_token = SocialToken.objects.filter(
        account__user=request.user,
        account__provider='github',
    ).exists()
    return 200, UserSchema(
        id=request.user.id,
        username=request.user.username,
        email=request.user.email or '',
        github_login=request.user.github_login,
        avatar_url=request.user.avatar_url,
        github_connected=has_token,
        is_staff=request.user.is_staff,
        is_superuser=request.user.is_superuser,
    )


@router.post('/logout')
def logout(request) -> dict:
    auth_logout(request)
    return {'ok': True}


class APITokenListItem(Schema):
    id: uuid.UUID
    name: str
    created_at: str
    last_used_at: Optional[str]


class APITokenCreated(Schema):
    id: uuid.UUID
    name: str
    token: str
    created_at: str


class CreateTokenRequest(Schema):
    name: str


@router.get('/tokens', response={200: list[APITokenListItem], 401: dict})
def list_tokens(request):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    tokens = APIToken.objects.filter(user=request.user, revoked_at__isnull=True)
    return 200, [
        APITokenListItem(
            id=t.id,
            name=t.name,
            created_at=t.created_at.isoformat(),
            last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        )
        for t in tokens
    ]


@router.post('/tokens', response={201: APITokenCreated, 401: dict})
def create_token(request, payload: CreateTokenRequest):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    name = payload.name.strip()
    if not name:
        raise HttpError(400, 'Token name is required')
    if APIToken.objects.filter(user=request.user, revoked_at__isnull=True).count() >= 20:
        raise HttpError(400, 'Maximum of 20 active tokens reached')
    raw_token = secrets.token_urlsafe(32)
    token = APIToken.objects.create(
        user=request.user,
        name=name,
        token_hash=APIToken.hash_token(raw_token),
    )
    return 201, APITokenCreated(
        id=token.id,
        name=token.name,
        token=raw_token,
        created_at=token.created_at.isoformat(),
    )


@router.delete('/tokens/{token_id}', response={204: None, 401: dict, 404: dict})
def revoke_token(request, token_id: uuid.UUID):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    try:
        token = APIToken.objects.get(id=token_id, user=request.user, revoked_at__isnull=True)
    except APIToken.DoesNotExist:
        raise HttpError(404, 'Token not found')
    token.revoked_at = timezone.now()
    token.save(update_fields=['revoked_at'])
    return 204, None
