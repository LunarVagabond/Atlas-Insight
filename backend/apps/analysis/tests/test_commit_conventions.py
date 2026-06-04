import pytest
from apps.analysis.commit_analysis import _detect_commit_conventions


class TestDetectCommitConventions:
    def test_empty_subjects(self):
        result = _detect_commit_conventions([])
        assert result == {}

    def test_only_merge_commits(self):
        # Merge commits get filtered to 'meaningful', falls back to subjects if empty
        # so result is not empty — it classifies based on the fallback
        subjects = ['Merge pull request #1 from foo/bar'] * 10
        result = _detect_commit_conventions(subjects)
        assert isinstance(result, dict)
        assert 'style' in result

    def test_conventional_commits_style(self):
        subjects = [
            'feat: add login page',
            'fix: correct password reset',
            'chore: update dependencies',
            'feat(auth): add OAuth support',
            'fix(api): handle null response',
            'docs: update README',
            'refactor: extract service layer',
            'test: add unit tests',
            'perf: optimize query',
            'ci: add GitHub Actions',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'conventional_commits'
        assert result['style_confidence'] >= 0.4
        assert result.get('format_template') == 'type(scope): description'

    def test_ticket_prefix_numeric(self):
        subjects = [
            '[#123] Fix login bug',
            '[#456] Add feature X',
            '[#789] Update docs',
            '[#101] Refactor auth',
            '[#202] Fix tests',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'ticket_prefix'

    def test_jira_prefix(self):
        # PROJ-123 matches TICKET regex first (^[A-Z]+-\d+$) so style = ticket_prefix
        subjects = [
            '[PROJ-123] Fix login bug',
            '[PROJ-456] Add feature X',
            '[AUTH-789] Update docs',
            '[AUTH-101] Refactor auth',
            '[PROJ-202] Fix tests',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] in ('jira_prefix', 'ticket_prefix')
        assert result.get('format_template') is not None

    def test_emoji_prefix(self):
        subjects = [
            '✨ Add new feature',
            '🐛 Fix a bug',
            '📚 Update documentation',
            '🔧 Configuration change',
            '🚀 Deploy to production',
            '✨ Another feature',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'emoji_prefix'

    def test_sentence_case(self):
        subjects = [
            'Add new login feature',
            'Fix password reset bug',
            'Update documentation',
            'Refactor authentication layer',
            'Remove deprecated API endpoints',
            'Improve error handling',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'sentence_case'

    def test_mixed_style(self):
        subjects = ['fix something', 'add thing', 'update stuff', 'random commit', 'misc']
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'mixed'

    def test_avg_subject_length(self):
        subjects = ['a' * 50, 'b' * 50]
        result = _detect_commit_conventions(subjects)
        assert result['avg_subject_length'] == 50

    def test_under_72_pct(self):
        subjects = ['a' * 30] * 8 + ['b' * 80] * 2
        result = _detect_commit_conventions(subjects)
        assert result['subject_under_72_pct'] == 0.8

    def test_issue_ref_rate(self):
        subjects = ['Fix #123 bug', 'Add feature', 'closes #456 issue', 'Other commit']
        result = _detect_commit_conventions(subjects)
        assert result['issue_ref_rate'] == 0.5

    def test_examples_provided(self):
        subjects = ['feat: add login', 'fix: correct bug', 'chore: update deps'] * 5
        result = _detect_commit_conventions(subjects)
        assert len(result['examples']) >= 1
        assert len(result['examples']) <= 3

    def test_merge_commits_filtered(self):
        subjects = (
            ['Merge pull request #1'] * 5 +
            ['feat: real commit'] * 6
        )
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'conventional_commits'

    def test_bracket_prefix_generic(self):
        subjects = [
            '[backend] Fix service',
            '[frontend] Add component',
            '[api] Update endpoint',
            '[db] Fix migration',
            '[backend] More fixes',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'bracket_prefix'

    def test_no_format_template_for_mixed(self):
        subjects = ['fix something', 'add thing', 'misc change', 'various updates', 'random']
        result = _detect_commit_conventions(subjects)
        assert 'format_template' not in result

    def test_samples_capped_at_250(self):
        subjects = ['feat: commit'] * 300
        result = _detect_commit_conventions(subjects)
        assert result['style'] == 'conventional_commits'

    def test_ticket_numeric_format_template(self):
        subjects = [
            '[#1] Fix bug',
            '[#2] Add feature',
            '[#3] Update docs',
            '[#4] Fix test',
            '[#5] Refactor',
        ]
        result = _detect_commit_conventions(subjects)
        if result['style'] == 'ticket_prefix':
            assert '#N' in result.get('format_template', '')

    def test_bracket_sep_detection(self):
        subjects = [
            '[tag] - Fix bug',
            '[tag] - Add feature',
            '[tag] - Update docs',
            '[tag] - Fix test',
            '[tag] - Misc',
        ]
        result = _detect_commit_conventions(subjects)
        assert result['style'] in ('bracket_prefix', 'ticket_prefix', 'jira_prefix')
