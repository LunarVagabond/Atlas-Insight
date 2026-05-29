from django.contrib import admin, messages
from django.utils.html import format_html

from .models import AnalysisRun, Repository


def _trigger(task_path, request, label):
    from importlib import import_module
    mod, attr = task_path.rsplit('.', 1)
    task = getattr(import_module(mod), attr)
    result = task.delay()
    messages.success(request, f'{label} queued (task id: {result.id})')


# ---------------------------------------------------------------------------
# Site-level actions (maintenance tasks — no queryset needed)
# ---------------------------------------------------------------------------

@admin.action(description='[Maintenance] Check stale repos (all)')
def action_check_stale(modeladmin, request, queryset):
    _trigger('apps.analysis.tasks.check_stale_repos', request, 'check_stale_repos')


@admin.action(description='[Maintenance] Cleanup old runs (all)')
def action_cleanup_runs(modeladmin, request, queryset):
    _trigger('apps.analysis.tasks.cleanup_old_runs', request, 'cleanup_old_runs')


@admin.action(description='[Maintenance] Evict stale clones (all)')
def action_evict_clones(modeladmin, request, queryset):
    _trigger('apps.analysis.tasks.evict_stale_clones', request, 'evict_stale_clones')


@admin.action(description='[Maintenance] Cleanup old logs (all)')
def action_cleanup_logs(modeladmin, request, queryset):
    _trigger('apps.analysis.tasks.cleanup_old_logs', request, 'cleanup_old_logs')


@admin.action(description='Mark selected repos as stale')
def action_mark_stale(modeladmin, request, queryset):
    updated = queryset.update(is_stale=True)
    messages.success(request, f'{updated} repo(s) marked stale.')


@admin.action(description='Clear stale flag on selected repos')
def action_clear_stale(modeladmin, request, queryset):
    updated = queryset.update(is_stale=False)
    messages.success(request, f'{updated} repo(s) stale flag cleared.')


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'url_link', 'last_commit_sha', 'is_stale', 'is_private', 'last_analyzed_at', 'last_fetched_at', 'created_at')
    list_filter = ('is_stale', 'is_private')
    search_fields = ('owner', 'name', 'url')
    readonly_fields = ('id', 'created_at', 'last_analyzed_at', 'last_fetched_at', 'last_commit_sha')
    actions = [
        action_check_stale,
        action_cleanup_runs,
        action_evict_clones,
        action_cleanup_logs,
        action_mark_stale,
        action_clear_stale,
    ]

    @admin.display(description='URL')
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)


# ---------------------------------------------------------------------------
# AnalysisRun admin actions
# ---------------------------------------------------------------------------

@admin.action(description='Re-trigger analysis for selected runs')
def action_rerun(modeladmin, request, queryset):
    from apps.analysis.tasks import analyze_repository
    count = 0
    for run in queryset.select_related('repo'):
        result = analyze_repository.delay(str(run.id))
        run.status = 'pending'
        run.celery_task_id = result.id
        run.save(update_fields=['status', 'celery_task_id'])
        count += 1
    messages.success(request, f'{count} run(s) re-queued.')


@admin.action(description='Mark selected runs as failed')
def action_mark_failed(modeladmin, request, queryset):
    updated = queryset.filter(status__in=['pending', 'running']).update(status='failed')
    messages.success(request, f'{updated} run(s) marked failed.')


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ('repo', 'user', 'status', 'celery_task_id', 'triggered_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('repo__owner', 'repo__name', 'celery_task_id')
    readonly_fields = ('id', 'triggered_at', 'completed_at', 'celery_task_id', 'result')
    raw_id_fields = ('repo', 'user')
    actions = [
        action_rerun,
        action_mark_failed,
        action_check_stale,
        action_cleanup_runs,
        action_evict_clones,
        action_cleanup_logs,
    ]
