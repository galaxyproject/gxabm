import json
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from abm.lib.config import create, kube, bootstrap, _extract_filename_from_url, _import_dataset_with_metadata
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


def test_config_create_backwards_compatible(temp_profiles, capsys):
    """Test creating a config with old format (backwards compatibility)."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_backwards', '/path/to/old/config'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == ''
    assert output['key'] == ''
    assert output['kube'] == '/path/to/old/config'


def test_config_create_mixed_precedence(temp_profiles, capsys):
    """Test that positional argument takes precedence over --kube flag."""
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['test_mixed', '/positional/path', '--kube', '/flag/path'])

    captured = capsys.readouterr()
    output = json.loads(captured.out.strip())

    assert output['url'] == ''
    assert output['key'] == ''
    assert output['kube'] == '/positional/path'  # Positional takes precedence


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


# Tests for new bootstrap functionality

def test_extract_filename_from_url():
    """Test filename extraction from URLs."""
    assert _extract_filename_from_url("https://example.com/data/file.fastq.gz") == "file.fastq.gz"
    assert _extract_filename_from_url("http://example.com/path/to/dataset.bam") == "dataset.bam"
    assert _extract_filename_from_url("https://example.com/data/") == "dataset"
    assert _extract_filename_from_url("https://example.com") == "dataset"


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_url_only(mock_dataset):
    """Test importing dataset with URL only (simple format)."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = "https://example.com/data/file.fastq"

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    mock_dataset._import_from_url.assert_called_once_with(
        mock_gi, history_id, "https://example.com/data/file.fastq", file_name="file.fastq"
    )


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_with_name(mock_dataset):
    """Test importing dataset with custom name."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = {
        "url": "https://example.com/data/file.fastq",
        "name": "custom_name"
    }

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    mock_dataset._import_from_url.assert_called_once_with(
        mock_gi, history_id, "https://example.com/data/file.fastq", file_name="custom_name"
    )


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_with_datatype(mock_dataset):
    """Test importing dataset with custom datatype."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = {
        "url": "https://example.com/data/file.fastq",
        "name": "custom_name",
        "datatype": "fastqsanger"
    }

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    mock_dataset._import_from_url.assert_called_once_with(
        mock_gi, history_id, "https://example.com/data/file.fastq",
        file_name="custom_name", file_type="fastqsanger"
    )


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_missing_url(mock_dataset, capsys):
    """Test importing dataset with missing URL."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = {"name": "custom_name"}

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    captured = capsys.readouterr()
    assert "ERROR: dataset config missing required 'url' field" in captured.out
    mock_dataset._import_from_url.assert_not_called()


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_invalid_config(mock_dataset, capsys):
    """Test importing dataset with invalid config format."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = 123  # Invalid type

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    captured = capsys.readouterr()
    assert "ERROR: dataset config must be URL string or dict" in captured.out
    mock_dataset._import_from_url.assert_not_called()


@pytest.fixture
def temp_bootstrap_config():
    """Create temporary bootstrap configuration files for testing."""
    configs = {}

    # Version 0 config (legacy)
    v0_config = {
        "datasets": {
            "Test History": [
                "https://example.com/file1.fastq",
                "https://example.com/file2.fastq"
            ]
        },
        "histories": ["https://example.com/history1"],
        "workflows": ["https://example.com/workflow1"]
    }

    # Version 1 config (new format)
    v1_config = {
        "version": 1,
        "datasets": {
            "Test History": [
                "https://example.com/file1.fastq",
                {
                    "url": "https://example.com/file2.fastq",
                    "name": "custom_file2"
                },
                {
                    "url": "https://example.com/file3.fastq",
                    "name": "custom_file3",
                    "datatype": "fastqsanger"
                }
            ]
        }
    }

    for version, config in [("v0", v0_config), ("v1", v1_config)]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            configs[version] = f.name

    yield configs

    # Clean up
    for config_file in configs.values():
        os.unlink(config_file)


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_version_0_backward_compatibility(mock_context_class, mock_connect, mock_history, mock_workflow, temp_bootstrap_config, capsys):
    """Test bootstrap with version 0 config (backward compatibility)."""
    mock_context = MagicMock()
    mock_context_class.return_value = mock_context

    mock_gi = MagicMock()
    mock_connect.return_value = mock_gi
    mock_gi.histories.create_history.return_value = {'id': 'new_history_id'}
    mock_gi.histories.get_histories.return_value = []

    context = Context('server', 'key', 'kubeconfig')
    config_file = temp_bootstrap_config['v0']

    with patch('abm.lib.config.dataset') as mock_dataset:
        bootstrap(context, ['test_server', config_file])

    captured = capsys.readouterr()
    assert "Processing bootstrap configuration version 0" in captured.out

    # Verify legacy import was called
    assert mock_dataset._import_from_url.call_count == 2


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_version_1_enhanced_format(mock_context_class, mock_connect, mock_history, mock_workflow, temp_bootstrap_config, capsys):
    """Test bootstrap with version 1 config (enhanced format)."""
    mock_context = MagicMock()
    mock_context_class.return_value = mock_context

    mock_gi = MagicMock()
    mock_connect.return_value = mock_gi
    mock_gi.histories.create_history.return_value = {'id': 'new_history_id'}
    mock_gi.histories.get_histories.return_value = []

    context = Context('server', 'key', 'kubeconfig')
    config_file = temp_bootstrap_config['v1']

    with patch('abm.lib.config.dataset') as mock_dataset:
        bootstrap(context, ['test_server', config_file])

    captured = capsys.readouterr()
    assert "Processing bootstrap configuration version 1" in captured.out

    # Verify enhanced import was called with different parameter sets
    calls = mock_dataset._import_from_url.call_args_list
    assert len(calls) == 3

    # Check that different parameter combinations were used
    assert calls[0][1]['file_name'] == "file1.fastq"  # URL only
    assert calls[1][1]['file_name'] == "custom_file2"  # Custom name
    assert calls[2][1]['file_name'] == "custom_file3"  # Custom name + datatype
    assert calls[2][1]['file_type'] == "fastqsanger"