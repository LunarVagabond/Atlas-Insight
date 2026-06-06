import collections
import re
from datetime import datetime, timedelta, timezone

from git import Repo

_CC_RE = re.compile(
    r'^(feat|fix|chore|docs|style|refactor|test|perf|ci|build|revert)(\(.+?\))?!?:\s',
    re.IGNORECASE,
)
_BRACKET_RE = re.compile(r'^\[([^\]]{1,40})\]')
_BRACKET_SEP_RE = re.compile(r'^\[[^\]]+\]\s*(?P<sep>-\s|:\s|—\s|\s)')
_ISSUE_REF_RE = re.compile(
    r'(\[#\d+\]|(?:^|\s)#\d+|\b(?:closes?|fixes?|resolves?)\s+#\d+)',
    re.IGNORECASE,
)
_EMOJI_RE = re.compile(r'^[\U0001F300-\U0001FAFF\U00002600-\U000027BF☀-➿]')
_TICKET_BRACKET_RE = re.compile(r'^[A-Z]+-\d+$|^#?\d+$')
_JIRA_BRACKET_RE = re.compile(r'^[A-Z]{2,10}-\d+$')
_MERGE_RE = re.compile(r'^Merge (pull request|branch|remote-tracking)', re.IGNORECASE)
_BOT_RE = re.compile(r'\[bot\]|dependabot|github-actions|renovate|snyk-bot|codecov', re.IGNORECASE)


def _detect_commit_conventions(subjects: list[str]) -> dict:
    if not subjects:
        return {}

    # Strip auto-generated merge commits — they don't reflect developer style
    meaningful = [s for s in subjects if not _MERGE_RE.match(s)]
    sample = (meaningful if meaningful else subjects)[:250]
    total = len(sample)
    if total == 0:
        return {}

    cc_count = sum(1 for m in sample if _CC_RE.match(m))

    bracket_matches = [_BRACKET_RE.match(m) for m in sample]
    bracket_count = sum(1 for m in bracket_matches if m)
    bracket_prefixes = [m.group(1) for m in bracket_matches if m]
    ticket_like_count = sum(1 for p in bracket_prefixes if _TICKET_BRACKET_RE.match(p))
    jira_like_count = sum(1 for p in bracket_prefixes if _JIRA_BRACKET_RE.match(p))

    emoji_count = sum(1 for m in sample if _EMOJI_RE.match(m))
    issue_ref_count = sum(1 for m in sample if _ISSUE_REF_RE.search(m))

    lengths = [len(m) for m in sample]
    avg_length = round(sum(lengths) / total)
    under_72_pct = round(sum(1 for ln in lengths if ln <= 72) / total, 2)

    cap_count = sum(1 for m in sample if m and m[0].isupper())

    style = 'mixed'
    style_confidence = 0.0

    if cc_count / total >= 0.4:
        style = 'conventional_commits'
        style_confidence = round(cc_count / total, 2)
    elif bracket_count / total >= 0.2:
        if bracket_count > 0 and ticket_like_count / bracket_count >= 0.5:
            style = 'ticket_prefix'
        elif bracket_count > 0 and jira_like_count / bracket_count >= 0.5:
            style = 'jira_prefix'
        else:
            style = 'bracket_prefix'
        style_confidence = round(bracket_count / total, 2)
    elif emoji_count / total >= 0.25:
        style = 'emoji_prefix'
        style_confidence = round(emoji_count / total, 2)
    elif cap_count / total >= 0.75:
        style = 'sentence_case'
        style_confidence = round(cap_count / total, 2)

    # Derive a human-readable format template
    format_template: str | None = None
    if style == 'conventional_commits':
        format_template = 'type(scope): description'
    elif style in ('ticket_prefix', 'jira_prefix', 'bracket_prefix') and bracket_count > 0:
        # Detect separator used after the bracket
        sep_sample = [m for m in sample if _BRACKET_RE.match(m)][:20]
        sep_counts: dict[str, int] = collections.Counter()
        for msg in sep_sample:
            m = _BRACKET_SEP_RE.match(msg)
            if m:
                sep_counts[m.group('sep').strip()] += 1
        sep = sep_counts.most_common(1)[0][0] if sep_counts else '-'
        sep_display = f' {sep} ' if sep else ' '
        if style == 'ticket_prefix':
            # Determine if numeric (#N) or alphanumeric (PROJ-N)
            numeric = sum(1 for p in bracket_prefixes if re.match(r'^#?\d+$', p))
            if numeric / max(ticket_like_count, 1) >= 0.7:
                format_template = f'[#N]{sep_display}description'
            else:
                format_template = f'[PROJ-N]{sep_display}description'
        elif style == 'jira_prefix':
            proj = next((p for p in bracket_prefixes if _JIRA_BRACKET_RE.match(p)), 'PROJ-N')
            prefix_part = re.sub(r'\d+', 'N', proj)
            format_template = f'[{prefix_part}]{sep_display}description'
        else:
            format_template = f'[tag]{sep_display}description'
    elif style == 'emoji_prefix':
        format_template = '✨ description'

    # Pick examples from structured commits first, then fill with others
    structured = [
        m for m in sample
        if _BRACKET_RE.match(m) or _CC_RE.match(m) or _EMOJI_RE.match(m)
    ]
    unstructured = [m for m in sample if m not in structured]
    candidate_pool = (structured + unstructured)[:80]
    examples: list[str] = []
    seen: set[str] = set()
    for msg in candidate_pool:
        key = msg[:80]
        if key not in seen:
            seen.add(key)
            examples.append(key)
        if len(examples) >= 3:
            break

    result: dict = {
        'style': style,
        'style_confidence': style_confidence,
        'avg_subject_length': avg_length,
        'subject_under_72_pct': under_72_pct,
        'issue_ref_rate': round(issue_ref_count / total, 2),
        'examples': examples,
    }
    if format_template:
        result['format_template'] = format_template
    return result


def analyze_commits(repo: Repo) -> dict:
    now = datetime.now(timezone.utc)
    commits = list(repo.iter_commits('HEAD'))

    # Weekly/monthly frequency (last 2 years)
    cutoff = now - timedelta(days=730)
    weekly: dict[str, int] = collections.defaultdict(int)
    monthly: dict[str, int] = collections.defaultdict(int)
    contributors: set[str] = set()
    contributor_by_period: dict[str, set] = collections.defaultdict(set)

    recent_90 = 0
    prior_90 = 0
    last_commit_date = None

    monthly_commits: dict[str, list] = collections.defaultdict(list)
    reverted_commits: list[dict] = []
    all_subjects: list[str] = []

    for commit in commits:
        dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
        if last_commit_date is None:
            last_commit_date = dt.isoformat()

        email = commit.author.email or ''
        name = commit.author.name or email
        if _BOT_RE.search(email) or _BOT_RE.search(name):
            subject = commit.message.split('\n')[0].strip()
            if subject and len(all_subjects) < 300:
                all_subjects.append(subject)
            continue
        # Deduplicate by name: same display name across different emails = same person
        identity = name.lower() or email.lower()
        contributors.add(identity)

        subject = commit.message.split('\n')[0].strip()
        if subject and len(all_subjects) < 300:
            all_subjects.append(subject)

        if dt >= cutoff:
            week_key = dt.strftime('%Y-W%W')
            month_key = dt.strftime('%Y-%m')
            weekly[week_key] += 1
            monthly[month_key] += 1
            contributor_by_period[month_key].add(identity)
            if len(monthly_commits[month_key]) < 60:
                subject = commit.message.split('\n')[0][:80]
                body_lines = commit.message[len(commit.message.split('\n')[0]):].strip()
                monthly_commits[month_key].append({
                    'sha': commit.hexsha[:7],
                    'message': subject,
                    'body': body_lines[:500] if body_lines else None,
                    'author': commit.author.name or commit.author.email,
                    'date': dt.date().isoformat(),
                    'parents': [p.hexsha[:7] for p in commit.parents],
                })

        if len(reverted_commits) < 100 and commit.message.strip().startswith('Revert '):
            try:
                files = list(commit.stats.files.keys())[:10]
            except Exception:
                files = []
            reverted_commits.append({
                'sha': commit.hexsha[:7],
                'message': commit.message.split('\n')[0][:120],
                'date': dt.date().isoformat(),
                'files': files,
            })

        delta = now - dt
        if delta.days <= 90:
            recent_90 += 1
        elif delta.days <= 180:
            prior_90 += 1

    activity_decay = round(recent_90 / max(prior_90, 1), 3)
    days_since_last = (
        (now - datetime.fromtimestamp(commits[0].committed_date, tz=timezone.utc)).days
        if commits
        else None
    )
    abandoned = days_since_last is not None and days_since_last > 365

    # Contributor churn per month
    months = sorted(contributor_by_period.keys())
    churn = []
    for i, m in enumerate(months):
        prev = contributor_by_period[months[i - 1]] if i > 0 else set()
        curr = contributor_by_period[m]
        churn.append(
            {
                'month': m,
                'active': len(curr),
                'new': len(curr - prev),
                'lost': len(prev - curr),
            }
        )

    return {
        'total_commits': len(commits),
        'total_contributors': len(contributors),
        'last_commit_date': last_commit_date,
        'days_since_last_commit': days_since_last,
        'abandoned': abandoned,
        'activity_decay_ratio': activity_decay,
        'weekly_frequency': [{'week': k, 'count': v} for k, v in sorted(weekly.items())],
        'monthly_frequency': [{'month': k, 'count': v} for k, v in sorted(monthly.items())],
        'contributor_churn': churn,
        'monthly_commits': dict(monthly_commits),
        'reverted_commits': reverted_commits,
        'commit_conventions': _detect_commit_conventions(all_subjects),
    }
