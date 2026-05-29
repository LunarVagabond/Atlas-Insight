import logging

from django.contrib.auth import logout as auth_logout
from ninja import Router, Schema
from ninja.errors import HttpError

logger = logging.getLogger(__name__)
router = Router(tags=['auth'])


class UserSchema(Schema):
    id: int
    username: str
    email: str
    github_login: str
    avatar_url: str


@router.get('/me', response={200: UserSchema, 401: dict})
def me(request):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    return 200, UserSchema(
        id=request.user.id,
        username=request.user.username,
        email=request.user.email or '',
        github_login=request.user.github_login,
        avatar_url=request.user.avatar_url,
    )


@router.post('/logout')
def logout(request) -> dict:
    auth_logout(request)
    return {'ok': True}
