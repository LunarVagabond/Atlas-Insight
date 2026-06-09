from django.conf import settings
from django.db import models
from uuid_extensions import uuid7

from apps.utils.encryption import EncryptedCharField


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
    auth_token = EncryptedCharField(blank=True, default='')
    auth_token_warning = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.IntegerField(default=0)
    scan_count = models.IntegerField(default=0)
    is_watched = models.BooleanField(default=False)
    cached_branch_count = models.IntegerField(null=True, blank=True, default=None)

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
    PROGRESS_STEP_CHOICES = [
        ('', ''),
        ('cloning', 'Cloning repository'),
        ('parsing', 'Parsing imports & structure'),
        ('heuristics', 'Computing heuristics'),
        ('metadata', 'Fetching GitHub metadata'),
        ('finalizing', 'Finalizing results'),
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
    progress_step = models.CharField(max_length=20, choices=PROGRESS_STEP_CHOICES, blank=True, default='')
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    branch = models.CharField(max_length=255, blank=True, default='')
    commit_sha = models.CharField(max_length=40, blank=True, default='')
    webhook_url = models.URLField(blank=True, default='')
    notification_email = models.EmailField(blank=True, default='')

    # --- error ---
    error_message = models.TextField(null=True, blank=True)

    # --- docs-only flag ---
    is_docs_only = models.BooleanField(default=False)

    # --- scalar columns (indexed for filtering/sorting) ---
    oss_score = models.FloatField(null=True, blank=True, db_index=True)
    oss_badge = models.CharField(max_length=20, null=True, blank=True)
    primary_language = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    github_stars = models.IntegerField(null=True, blank=True, db_index=True)
    total_commits = models.IntegerField(null=True, blank=True)
    total_contributors = models.IntegerField(null=True, blank=True)
    days_since_last_commit = models.IntegerField(null=True, blank=True)
    abandoned = models.BooleanField(null=True, blank=True, db_index=True)
    bus_factor = models.IntegerField(null=True, blank=True)
    security_issue_count = models.IntegerField(null=True, blank=True)
    dependency_count = models.IntegerField(null=True, blank=True)
    test_ratio = models.FloatField(null=True, blank=True)
    archived = models.BooleanField(null=True, blank=True, db_index=True)

    # --- per-module JSON fields ---
    commits_data = models.JSONField(null=True, blank=True)
    graph_data = models.JSONField(null=True, blank=True)
    deps_data = models.JSONField(null=True, blank=True)
    heuristics_data = models.JSONField(null=True, blank=True)
    oss_score_data = models.JSONField(null=True, blank=True)
    readme_data = models.JSONField(null=True, blank=True)
    structure_data = models.JSONField(null=True, blank=True)
    security_data = models.JSONField(null=True, blank=True)
    github_meta_data = models.JSONField(null=True, blank=True)
    classification_data = models.JSONField(null=True, blank=True)
    todos_data = models.JSONField(null=True, blank=True)
    arch_tours_data = models.JSONField(null=True, blank=True)
    ownership_data = models.JSONField(null=True, blank=True)
    contribution_opportunities_data = models.JSONField(null=True, blank=True)
    repo_type_data = models.JSONField(null=True, blank=True)
    license_data = models.JSONField(null=True, blank=True)
    complexity_data = models.JSONField(null=True, blank=True)
    dead_code_data = models.JSONField(null=True, blank=True)
    test_coverage_data = models.JSONField(null=True, blank=True)
    containers_data = models.JSONField(null=True, blank=True)
    cicd_data = models.JSONField(null=True, blank=True)
    tools_data = models.JSONField(null=True, blank=True)
    changelog_data = models.JSONField(null=True, blank=True)
    diff_data = models.JSONField(null=True, blank=True)
    similar_runs_data = models.JSONField(null=True, blank=True)
    issues_data = models.JSONField(null=True, blank=True)
    pr_refs_data = models.JSONField(null=True, blank=True)

    @property  # type: ignore[override]
    def result(self) -> dict | None:
        if self.error_message:
            return {'error': self.error_message}
        _pairs = [
            ('commits', self.commits_data),
            ('graph', self.graph_data),
            ('dependencies', self.deps_data),
            ('heuristics', self.heuristics_data),
            ('oss_score', self.oss_score_data),
            ('readme', self.readme_data),
            ('structure', self.structure_data),
            ('security', self.security_data),
            ('github_meta', self.github_meta_data),
            ('classification', self.classification_data),
            ('todos', self.todos_data),
            ('arch_tours', self.arch_tours_data),
            ('ownership', self.ownership_data),
            ('contribution_opportunities', self.contribution_opportunities_data),
            ('repo_type', self.repo_type_data),
            ('license', self.license_data),
            ('complexity', self.complexity_data),
            ('dead_code', self.dead_code_data),
            ('test_coverage', self.test_coverage_data),
            ('containers', self.containers_data),
            ('cicd', self.cicd_data),
            ('tools', self.tools_data),
            ('changelog', self.changelog_data),
            ('diff', self.diff_data),
            ('similar_runs', self.similar_runs_data),
            ('issues', self.issues_data),
            ('pr_refs', self.pr_refs_data),
        ]
        data = {k: v for k, v in _pairs if v is not None}
        if not data:
            return None
        if self.oss_score_data:
            mode = self.oss_score_data.get('mode')
            if mode:
                data['scoring_mode'] = mode
            mode_reason = self.oss_score_data.get('mode_reason')
            if mode_reason:
                data['scoring_mode_reason'] = mode_reason
        if self.is_docs_only:
            data['is_docs_only'] = True
        return data

    @result.setter
    def result(self, value: dict | None) -> None:
        if value is None:
            self.error_message = None
            return
        if isinstance(value, dict) and set(value.keys()) <= {'error'}:
            self.error_message = value.get('error')
            return
        oss_raw = value.get('oss_score')
        if isinstance(oss_raw, dict):
            oss_raw = dict(oss_raw)
            mode_reason = value.get('scoring_mode_reason')
            if mode_reason:
                oss_raw['mode_reason'] = mode_reason
            self.oss_score = oss_raw.get('score')
            self.oss_badge = oss_raw.get('badge') or ''
            self.oss_score_data = oss_raw
        else:
            self.oss_score = None
            self.oss_badge = ''
            self.oss_score_data = None
        gm = value.get('github_meta') or {}
        self.primary_language = gm.get('primary_language') or ''
        self.github_stars = gm.get('stars')
        self.archived = gm.get('archived')
        cm = value.get('commits') or {}
        self.total_commits = cm.get('total_commits')
        self.total_contributors = cm.get('total_contributors')
        self.days_since_last_commit = cm.get('days_since_last_commit')
        self.abandoned = cm.get('abandoned')
        st = value.get('structure') or {}
        self.bus_factor = st.get('bus_factor')
        sec = value.get('security') or {}
        self.security_issue_count = sec.get('issue_count')
        deps = value.get('dependencies') or {}
        self.dependency_count = deps.get('dependency_count')
        tc = value.get('test_coverage') or {}
        self.test_ratio = tc.get('test_ratio')
        self.is_docs_only = bool(value.get('is_docs_only', False))
        self.error_message = None
        self.commits_data = value.get('commits')
        self.graph_data = value.get('graph')
        self.deps_data = value.get('dependencies')
        self.heuristics_data = value.get('heuristics')
        self.readme_data = value.get('readme')
        self.structure_data = value.get('structure')
        self.security_data = value.get('security')
        self.github_meta_data = value.get('github_meta')
        self.classification_data = value.get('classification')
        self.todos_data = value.get('todos')
        self.arch_tours_data = value.get('arch_tours')
        self.ownership_data = value.get('ownership')
        self.contribution_opportunities_data = value.get('contribution_opportunities')
        self.repo_type_data = value.get('repo_type')
        self.license_data = value.get('license')
        self.complexity_data = value.get('complexity')
        self.dead_code_data = value.get('dead_code')
        self.test_coverage_data = value.get('test_coverage')
        self.containers_data = value.get('containers')
        self.cicd_data = value.get('cicd')
        self.tools_data = value.get('tools')
        self.changelog_data = value.get('changelog')
        self.diff_data = value.get('diff')
        self.similar_runs_data = value.get('similar_runs')
        self.issues_data = value.get('issues')
        self.pr_refs_data = value.get('pr_refs')

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


class WebhookDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    delivery_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    repo_url = models.CharField(max_length=500, blank=True, default='')
    triggered_reanalysis = models.BooleanField(default=False)
    run = models.ForeignKey(
        'AnalysisRun', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='webhook_deliveries',
    )
    received_at = models.DateTimeField(auto_now_add=True)
    raw_payload = models.JSONField(blank=True, default=dict)

    class Meta:
        ordering = ['-received_at']
        verbose_name_plural = 'webhook deliveries'

    def __str__(self):
        return f'{self.event_type} {self.delivery_id[:8]} ({self.received_at:%Y-%m-%d %H:%M})'


class FeatureFlag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({"on" if self.enabled else "off"})'


class Constellation(models.Model):
    """MS1: meta-layer linking multiple repos that reference each other."""
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255)
    org = models.CharField(max_length=255, blank=True, null=True)
    repos = models.ManyToManyField(Repository, related_name='constellations', blank=True)
    edges = models.JSONField(default=list, blank=True)
    # edges schema: [{from_repo_id, to_repo_id, ref_type: 'hard'|'soft', evidence: str}]
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
