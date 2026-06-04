import tempfile
from pathlib import Path

import pytest
from apps.analysis.project_structure.community import (
    detect_license_type,
    parse_license_spdx_from_content,
    parse_roadmap_file,
    read_community_files,
)


class TestDetectLicenseType:
    def test_mit_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('MIT License\n\nPermission is hereby granted, free of charge...')
            result = detect_license_type(p)
        assert result == 'MIT'

    def test_apache_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('Apache License, Version 2.0')
            result = detect_license_type(p)
        assert result == 'Apache-2.0'

    def test_gpl3_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('GNU General Public License version 3')
            result = detect_license_type(p)
        assert result == 'GPL-3.0'

    def test_isc_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('ISC License\nCopyright...')
            result = detect_license_type(p)
        assert result == 'ISC'

    def test_unlicense(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('This is free and unencumbered software released into the public domain.')
            result = detect_license_type(p)
        assert result == 'Unlicense'

    def test_other_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('Some custom proprietary license text here.')
            result = detect_license_type(p)
        assert result == 'Other'

    def test_lgpl_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('GNU Lesser General Public License version 2')
            result = detect_license_type(p)
        assert result in ('LGPL-2.1', 'LGPL')

    def test_gpl_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('GNU General Public License')
            result = detect_license_type(p)
        assert result in ('GPL-2.0', 'GPL-3.0', 'GPL')

    def test_nonexistent_file(self):
        result = detect_license_type(Path('/nonexistent/LICENSE'))
        assert result is None

    def test_bsd3_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('Neither the name of the project nor the names of its contributors')
            result = detect_license_type(p)
        assert result == 'BSD-3-Clause'

    def test_mpl_license(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'LICENSE'
            p.write_text('Mozilla Public License 2.0')
            result = detect_license_type(p)
        assert result == 'MPL-2.0'


class TestParseLicenseSpdxFromContent:
    def test_mit(self):
        assert parse_license_spdx_from_content('permission is hereby granted') == 'MIT'

    def test_apache(self):
        assert parse_license_spdx_from_content('Apache License, Version 2.0') == 'Apache-2.0'

    def test_no_match(self):
        assert parse_license_spdx_from_content('some random text') is None

    def test_case_insensitive(self):
        assert parse_license_spdx_from_content('MIT LICENSE\nPERMISSION IS HEREBY GRANTED') == 'MIT'


class TestReadCommunityFiles:
    def test_reads_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'CONTRIBUTING.md').write_text('# Contributing\nPRs welcome.')
            result = read_community_files(base, contributing='CONTRIBUTING.md', license_f=None, coc=None, security=None, changelog=None)
        assert result['contributing'] == '# Contributing\nPRs welcome.'

    def test_none_filename_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            result = read_community_files(base, contributing=None, license_f=None, coc=None, security=None, changelog=None)
        assert result['contributing'] is None

    def test_truncates_long_file(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'CONTRIBUTING.md').write_text('x' * 20_000)
            result = read_community_files(base, contributing='CONTRIBUTING.md', license_f=None, coc=None, security=None, changelog=None)
        assert len(result['contributing']) <= 12_100
        assert 'truncated' in result['contributing']

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            result = read_community_files(base, contributing='CONTRIBUTING.md', license_f=None, coc=None, security=None, changelog=None)
        assert result['contributing'] is None

    def test_reads_all_files(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'LICENSE').write_text('MIT License')
            (base / 'CONTRIBUTING.md').write_text('# Contributing')
            result = read_community_files(
                base,
                contributing='CONTRIBUTING.md',
                license_f='LICENSE',
                coc=None, security=None, changelog=None
            )
        assert result['license'] == 'MIT License'
        assert result['contributing'] == '# Contributing'
        assert result['coc'] is None


class TestParseRoadmapFile:
    def test_no_roadmap_file(self):
        result = parse_roadmap_file(Path('/tmp'), None)
        assert result is None

    def test_parses_roadmap(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'ROADMAP.md').write_text('## Q1 2025\n- Task A\n- Task B\n')
            result = parse_roadmap_file(base, 'ROADMAP.md')
        assert result is not None
        assert 'milestones' in result
        assert len(result['milestones']) == 1

    def test_missing_roadmap_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            result = parse_roadmap_file(base, 'ROADMAP.md')
        assert result is None
