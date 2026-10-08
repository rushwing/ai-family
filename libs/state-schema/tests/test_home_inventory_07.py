"""TC-013-07: invoke the real offline CLI, never a test-side validator."""

import json
import os
import stat

import pytest
from inventory_support import EXAMPLE, changed, runtime_required
from test_home_inventory_04 import edited_copy

pytestmark = runtime_required


def test_cli_public_fixture_and_unicode_private_copy(api, inventory, tmp_path, cli):
    original = EXAMPLE.read_bytes()
    public = cli(EXAMPLE)
    assert public.returncode == 0, public.stderr
    assert json.loads(public.stdout) == api.load_inventory(EXAMPLE)
    data = edited_copy(inventory)
    data['areas'][1]['name'] = 'Fictional chambre été'
    path = tmp_path / 'fictional copy été.home-inventory.local.json'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    before = path.read_bytes()
    private = cli(path)
    assert private.returncode == 0, private.stderr
    assert json.loads(private.stdout) == data
    assert path.read_bytes() == before
    assert EXAMPLE.read_bytes() == original


@pytest.mark.parametrize('case,path_token', [
    ('json', None), ('version', 'schema_version'), ('field', 'unexpected'),
    ('reference', 'area_id'), ('missing', None), ('utf8', None), ('unreadable', None),
])
def test_cli_actionable_repeatable_failures(inventory, tmp_path, cli, case, path_token):
    path = tmp_path / 'fictional invalid inventory.json'
    if case == 'unreadable' and os.geteuid() == 0:
        pytest.skip('Root bypasses permissions; unreadable-file case needs an unprivileged user')
    if case == 'json':
        path.write_text('{ broken', encoding='utf-8')
    elif case == 'utf8':
        path.write_bytes(b'\xff\xfe\xfa')
    elif case != 'missing':
        data = inventory
        if case == 'version':
            data = changed(data, ('schema_version',), 2)
        elif case == 'field':
            data = changed(data, ('areas', 0, 'unexpected'), 'typo')
        elif case == 'reference':
            data = changed(data, ('devices', 0, 'area_id'), 'missing-area')
        path.write_text(json.dumps(data), encoding='utf-8')
    before = path.read_bytes() if path.exists() else None
    if case == 'unreadable':
        path.chmod(0)
    try:
        first, second = cli(path), cli(path)
        cause_terms = {
            'json': ('json', 'parse', 'expecting', 'decode'),
            'utf8': ('utf', 'encoding', 'decode'),
            'missing': ('no such', 'not found', 'missing'),
            'unreadable': ('permission', 'denied', 'unreadable'),
        }
        for result in (first, second):
            assert result.returncode != 0
            assert not result.stdout.strip(), 'Failed loads must not emit a successful inventory'
            assert str(path) in result.stderr
            assert result.stderr.strip()
            if path_token:
                assert path_token in result.stderr
            else:
                assert any(term in result.stderr.lower() for term in cause_terms[case])
        assert first.returncode == second.returncode
        assert first.stderr == second.stderr
        if case == 'unreadable':
            assert stat.S_IMODE(path.stat().st_mode) == 0
    finally:
        if case == 'unreadable':
            path.chmod(0o600)
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize('content,path_token', [
    ('{"schema_version":1,"schema_version":2}', 'schema_version'),
    ('{"home":{"id":"first","id":"second"}}', 'home.id'),
    ('{"areas":[{"name":"first","name":"second"}]}', 'areas[0].name'),
    ('{"schema_version":NaN}', 'NaN'),
    ('{"schema_version":Infinity}', 'Infinity'),
    ('{"schema_version":-Infinity}', '-Infinity'),
])
def test_cli_rejects_duplicate_fields_and_nonstandard_json(tmp_path, cli, content, path_token):
    path = tmp_path / 'ambiguous.json'
    path.write_text(content, encoding='utf-8')
    before = path.read_bytes()
    result = cli(path)
    assert result.returncode != 0
    assert not result.stdout.strip()
    assert str(path) in result.stderr
    assert path_token in result.stderr
    assert path.read_bytes() == before
