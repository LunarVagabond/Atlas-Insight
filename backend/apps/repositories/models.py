from django.db import models


class Repository(models.Model):
    url = models.URLField(unique=True)
    owner = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    last_commit_sha = models.CharField(max_length=40, blank=True, default='')
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f'{self.repo} run #{self.pk} ({self.status})'
