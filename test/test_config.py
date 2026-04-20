import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

from abm.lib.config import create, kube
from abm.lib.common import Context


@pytest.fixture
def temp_profiles():
    """Create a temporary profiles.yml file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write("test_profile:\n  url: 'http://example.com'\n  key: 'test_key'\n  kube: '/tmp/test.config'\n")
        temp_file = f.name

    with patch('abm.lib.common.find_config') as mock_find:
        mock_find.return_value = temp_file
        yield temp_file

    # Clean up
    os.unlink(temp_file)


def test_config_create_minimal(temp_profiles, capsys):
    """Test creating a config with just profile name."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_new'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == ''
    assert output['key'] == ''
    assert output['kube'] == ''


def test_config_create_with_url(temp_profiles, capsys):
    """Test creating a config with URL specified."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_new', '--url', 'https://galaxy.example.com'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == 'https://galaxy.example.com'
    assert output['key'] == ''
    assert output['kube'] == ''


def test_config_create_with_key(temp_profiles, capsys):
    """Test creating a config with API key specified."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_new', '--key', 'my_api_key'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == ''
    assert output['key'] == 'my_api_key'
    assert output['kube'] == ''


def test_config_create_with_kube(temp_profiles, capsys):
    """Test creating a config with kubeconfig path specified."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_new', '--kube', '/path/to/kube.config'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == ''
    assert output['key'] == ''
    assert output['kube'] == '/path/to/kube.config'


def test_config_create_with_all_params(temp_profiles, capsys):
    """Test creating a config with all parameters specified."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, [
        'test_new',
        '--url', 'https://galaxy.example.com',
        '--key', 'my_api_key',
        '--kube', '/path/to/kube.config'
    ])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == 'https://galaxy.example.com'
    assert output['key'] == 'my_api_key'
    assert output['kube'] == '/path/to/kube.config'


def test_config_create_duplicate_profile(temp_profiles, capsys):
    """Test creating a config with existing profile name should fail."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_profile'])  # This profile already exists in fixture

    captured = capsys.readouterr()
    assert "ERROR: a cloud configuration with that name already exists." in captured.out


def test_config_create_missing_profile_name(temp_profiles):
    """Test creating a config without profile name should fail with SystemExit."""
    context = Context('server', 'key', 'kubeconfig')

    with pytest.raises(SystemExit):
        create(context, [])


def test_config_create_help(temp_profiles):
    """Test that help argument works."""
    context = Context('server', 'key', 'kubeconfig')

    with pytest.raises(SystemExit):
        create(context, ['--help'])


def test_config_kube_success(temp_profiles, capsys):
    """Test setting kube path for existing profile."""
    context = Context('server', 'key', 'kubeconfig')

    kube(context, ['test_profile', '/new/path/to/config'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == 'http://example.com'
    assert output['key'] == 'test_key'
    assert output['kube'] == '/new/path/to/config'


def test_config_kube_unknown_profile(temp_profiles, capsys):
    """Test setting kube path for unknown profile."""
    context = Context('server', 'key', 'kubeconfig')

    kube(context, ['unknown_profile', '/path/to/config'])

    captured = capsys.readouterr()
    assert "ERROR: Unknown cloud unknown_profile" in captured.out


def test_config_kube_invalid_args(temp_profiles, capsys):
    """Test kube command with invalid argument count."""
    context = Context('server', 'key', 'kubeconfig')

    # Test with only one argument
    kube(context, ['test_profile'])

    captured = capsys.readouterr()
    assert "USAGE: abm config kube <cloud> <kube_path>" in captured.out

    # Test with no arguments
    kube(context, [])

    captured = capsys.readouterr()
    assert "USAGE: abm config kube <cloud> <kube_path>" in captured.out