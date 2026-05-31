from django.conf import settings
from django.db import models
from uuid_extensions import uuid7


class Repository(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    url = models.URLField(unique=True)
    owner = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    last_commit_sha = models.CharField(max_length=40, blank=True, default='')
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    is_stale = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    auth_token = models.CharField(max_length=255, blank=True, default='')
    auth_token_warning = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.IntegerField(default=0)
    scan_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'repositories'

    def __str__(self):
        return f'{self.owner}/{self.name}'


class AnalysisRun(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='runs')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='runs',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    webhook_url = models.URLField(blank=True, default='')
    notification_email = models.EmailField(blank=True, default='')

    def __str__(self):
        return f'{self.repo} run {self.pk} ({self.status})'


class UserFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'repo')]

    def __str__(self):
        return f'{self.user} → {self.repo}'


class RepoOfTheWeek(models.Model):
    repo = models.ForeignKey(Repository, on_delete=models.PROTECT, related_name='spotlights')
    week_start = models.DateField()
    selected_at = models.DateTimeField(auto_now_add=True)
    pick_number = models.IntegerField()

    class Meta:
        ordering = ['-week_start']
        unique_together = [('repo', 'week_start')]

    def __str__(self):
        return f'{self.repo} — week of {self.week_start}'
