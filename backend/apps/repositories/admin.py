from django.contrib import admin

from .models import AnalysisRun, Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'last_commit_sha', 'last_analyzed_at', 'created_at')
    search_fields = ('owner', 'name', 'url')


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ('repo', 'status', 'triggered_at', 'completed_at')
    list_filter = ('status',)
