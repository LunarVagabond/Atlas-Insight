import pytest
from apps.analysis.roadmap_parser import (
    _classify_item,
    _extract_date,
    _finalize,
    parse_roadmap,
)


class TestExtractDate:
    def test_year_quarter_format(self):
        assert _extract_date('2025-Q1') == '2025-Q1'

    def test_quarter_year_format(self):
        assert _extract_date('Q2 2026') == '2026-Q2'

    def test_quarter_slash_year(self):
        assert _extract_date('Q3/2025') == '2025-Q3'

    def test_month_year_full(self):
        assert _extract_date('January 2025') == '2025-01'

    def test_month_year_abbreviated(self):
        assert _extract_date('Feb 2026') == '2026-02'

    def test_yyyy_mm(self):
        assert _extract_date('2025-07') == '2025-07'

    def test_bare_year(self):
        assert _extract_date('2027') == '2027'

    def test_no_date(self):
        assert _extract_date('no date here') is None

    def test_case_insensitive_month(self):
        assert _extract_date('MARCH 2025') == '2025-03'

    def test_december(self):
        assert _extract_date('December 2025') == '2025-12'

    def test_may_abbreviation(self):
        # 'may' is both full and abbreviation
        result = _extract_date('May 2025')
        assert result == '2025-05'


class TestClassifyItem:
    def test_plain_list_dash(self):
        result = _classify_item('- Add feature X')
        assert result == ('todo', 'Add feature X')

    def test_plain_list_plus(self):
        result = _classify_item('+ Add feature X')
        assert result == ('todo', 'Add feature X')

    def test_plain_list_asterisk(self):
        result = _classify_item('* Add feature X')
        assert result == ('todo', 'Add feature X')

    def test_numbered_list(self):
        result = _classify_item('1. First item')
        assert result == ('todo', 'First item')

    def test_checkbox_done_lowercase(self):
        result = _classify_item('- [x] Done task')
        assert result == ('done', 'Done task')

    def test_checkbox_done_uppercase(self):
        result = _classify_item('- [X] Done task')
        assert result == ('done', 'Done task')

    def test_checkbox_todo(self):
        result = _classify_item('- [ ] Todo task')
        assert result == ('todo', 'Todo task')

    def test_strikethrough_done(self):
        result = _classify_item('- ~~Completed feature~~')
        assert result == ('done', 'Completed feature')

    def test_not_a_list_item(self):
        assert _classify_item('Just a paragraph') is None

    def test_empty_line(self):
        assert _classify_item('') is None

    def test_indented_item(self):
        result = _classify_item('  - Indented item')
        assert result == ('todo', 'Indented item')

    def test_done_prefix_bold(self):
        result = _classify_item('- **Done:** Spotlight feature')
        assert result == ('done', 'Spotlight feature')

    def test_done_prefix_plain(self):
        result = _classify_item('- Completed: shipped API')
        assert result == ('done', 'shipped API')

    def test_done_suffix(self):
        result = _classify_item('- Feature X (done)')
        assert result == ('done', 'Feature X')

    def test_done_emoji_prefix(self):
        result = _classify_item('- ✅ Released v2')
        assert result == ('done', 'Released v2')

    def test_inline_strikethrough(self):
        result = _classify_item('- ~~partial~~ strike')
        assert result == ('done', 'partial strike')

    def test_context_done_subsection(self):
        result = _classify_item('- Legacy API removal', context_done=True)
        assert result == ('done', 'Legacy API removal')


class TestFinalize:
    def test_all_todo(self):
        result = _finalize('Phase 1', ['- Item A', '- Item B'])
        assert result['status'] == 'planned'
        assert result['todo_count'] == 2
        assert result['done_count'] == 0

    def test_all_done(self):
        result = _finalize('Phase 1', ['- [x] Done A', '- [x] Done B'])
        assert result['status'] == 'done'
        assert result['done_count'] == 2
        assert result['todo_count'] == 0

    def test_mixed_in_progress(self):
        result = _finalize('Phase 1', ['- [x] Done A', '- Todo B'])
        assert result['status'] == 'in-progress'

    def test_date_from_title(self):
        result = _finalize('Q1 2025', ['- Item'])
        assert result['date'] == '2025-Q1'

    def test_date_from_body(self):
        result = _finalize('Phase 1', ['Target: March 2025', '- Item'])
        assert result['date'] == '2025-03'

    def test_strips_markdown_links(self):
        result = _finalize('Phase', ['- [Feature X](https://example.com)'])
        assert result['todo_items'][0] == 'Feature X'

    def test_strips_inline_formatting(self):
        result = _finalize('Phase', ['- **bold text**'])
        assert result['todo_items'][0] == 'bold text'

    def test_caps_items_at_6(self):
        lines = [f'- Item {i}' for i in range(10)]
        result = _finalize('Phase', lines)
        assert len(result['todo_items']) == 6
        assert result['todo_count'] == 10

    def test_empty_lines_skipped(self):
        result = _finalize('Phase', ['', '- Item A', ''])
        assert result['todo_count'] == 1

    def test_informational_title(self):
        result = _finalize('How to read this', ['- Near-term means soon', '- Medium-term means later'])
        assert result['kind'] == 'informational'
        assert result['status'] == 'informational'
        assert result['notes'] == ['Near-term means soon', 'Medium-term means later']
        assert result['todo_count'] == 0

    def test_prose_notes(self):
        result = _finalize('Phase 1', ['Gate work before release.', '- Task A'])
        assert result['notes'] == ['Gate work before release.']
        assert result['todo_count'] == 1

    def test_subsection_done_context(self):
        lines = ['**Done**', '- Shipped auth', '- Shipped billing', '**Up next**', '- Payments']
        result = _finalize('Features', lines)
        assert result['done_count'] == 2
        assert result['todo_count'] == 1
        assert 'Shipped auth' in result['done_items']
        assert 'Payments' in result['todo_items']

    def test_kind_and_notes_fields(self):
        result = _finalize('Phase', ['- Item'])
        assert result['kind'] == 'milestone'
        assert result['notes'] == []


class TestParseRoadmap:
    def test_empty_content(self):
        result = parse_roadmap('')
        assert result == {'milestones': []}

    def test_no_headings(self):
        result = parse_roadmap('Just some text\n- item')
        assert result == {'milestones': []}

    def test_single_milestone_with_items(self):
        content = '## Phase 1\n- Task A\n- Task B\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 1
        assert result['milestones'][0]['title'] == 'Phase 1'
        assert result['milestones'][0]['todo_count'] == 2

    def test_multiple_milestones(self):
        content = '## Q1 2025\n- Task A\n## Q2 2025\n- Task B\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 2

    def test_empty_sections_dropped(self):
        content = '## Section A\nsome prose\n## Section B\n- Task\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 1
        assert result['milestones'][0]['title'] == 'Section B'

    def test_section_kept_if_has_date(self):
        content = '## Q1 2025\nJust some text, no items\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 1
        assert result['milestones'][0]['date'] == '2025-Q1'

    def test_caps_at_24_milestones(self):
        lines = []
        for i in range(30):
            lines.append(f'## Milestone {i}')
            lines.append(f'- Task {i}')
        result = parse_roadmap('\n'.join(lines))
        assert len(result['milestones']) == 24

    def test_done_status(self):
        content = '## Completed\n- [x] Task A\n- [x] Task B\n'
        result = parse_roadmap(content)
        assert result['milestones'][0]['status'] == 'done'

    def test_h1_through_h4_headings(self):
        content = '# H1\n- A\n## H2\n- B\n### H3\n- C\n#### H4\n- D\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 4

    def test_returns_dict_structure(self):
        content = '## Phase 1\n- Item\n'
        result = parse_roadmap(content)
        m = result['milestones'][0]
        assert 'title' in m
        assert 'date' in m
        assert 'kind' in m
        assert 'status' in m
        assert 'done_count' in m
        assert 'todo_count' in m
        assert 'done_items' in m
        assert 'todo_items' in m
        assert 'notes' in m

    def test_informational_section_included(self):
        content = '## How to read this\n- Tier one\n- Tier two\n## Phase 1\n- Task\n'
        result = parse_roadmap(content)
        assert len(result['milestones']) == 2
        assert result['milestones'][0]['kind'] == 'informational'
        assert result['milestones'][1]['kind'] == 'milestone'

    def test_done_prefix_in_roadmap(self):
        content = '## Self-hosted\n- **Done:** Feature flags\n- Extend flags\n'
        result = parse_roadmap(content)
        m = result['milestones'][0]
        assert m['done_count'] == 1
        assert m['todo_count'] == 1
        assert 'Feature flags' in m['done_items']
