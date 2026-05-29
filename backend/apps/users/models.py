from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    github_login = models.CharField(max_length=255, blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')

    def __str__(self):
        return self.github_login or self.username
