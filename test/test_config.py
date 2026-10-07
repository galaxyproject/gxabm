import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from abm.lib.common import Context
from abm.lib.config import (
    _extract_filename_from_url,
    _import_dataset_with_metadata,
    bootstrap,
    create,
    kube,
)


@pytest.fixture
def temp_profiles():
    """Create a temporary profiles.yml file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(
            "test_profile:\n  url: 'http://example.com'\n  key: 'test_key'\n  kube: '/tmp/test.config'\n"
        )
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

    create(
        context,
        [
            'test_new',
            '--url',
            'https://galaxy.example.com',
            '--key',
            'my_api_key',
            '--kube',
            '/path/to/kube.config',
        ],
    )

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
    assert (
        _extract_filename_from_url("https://example.com/data/file.fastq.gz")
        == "file.fastq.gz"
    )
    assert (
        _extract_filename_from_url("http://example.com/path/to/dataset.bam")
        == "dataset.bam"
    )
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
        mock_gi,
        history_id,
        "https://example.com/data/file.fastq",
        file_name="file.fastq",
    )


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_with_name(mock_dataset):
    """Test importing dataset with custom name."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = {
        "url": "https://example.com/data/file.fastq",
        "name": "custom_name",
    }

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    mock_dataset._import_from_url.assert_called_once_with(
        mock_gi,
        history_id,
        "https://example.com/data/file.fastq",
        file_name="custom_name",
    )


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_with_datatype(mock_dataset):
    """Test importing dataset with custom datatype."""
    mock_gi = MagicMock()
    history_id = "test_history_id"
    dataset_config = {
        "url": "https://example.com/data/file.fastq",
        "name": "custom_name",
        "datatype": "fastqsanger",
    }

    _import_dataset_with_metadata(mock_gi, history_id, dataset_config)

    mock_dataset._import_from_url.assert_called_once_with(
        mock_gi,
        history_id,
        "https://example.com/data/file.fastq",
        file_name="custom_name",
        file_type="fastqsanger",
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
                "https://example.com/file2.fastq",
            ]
        },
        "histories": ["https://example.com/history1"],
        "workflows": ["https://example.com/workflow1"],
    }

    # Version 1 config (new format)
    v1_config = {
        "version": 1,
        "datasets": {
            "Test History": [
                "https://example.com/file1.fastq",
                {"url": "https://example.com/file2.fastq", "name": "custom_file2"},
                {
                    "url": "https://example.com/file3.fastq",
                    "name": "custom_file3",
                    "datatype": "fastqsanger",
                },
            ]
        },
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
def test_bootstrap_version_0_backward_compatibility(
    mock_context_class,
    mock_connect,
    mock_history,
    mock_workflow,
    temp_bootstrap_config,
    capsys,
):
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

    # The v0 (legacy) dataset config still imports both datasets; the version
    # attribute is now ignored (issue #349).
    assert mock_dataset._import_from_url.call_count == 2


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_version_1_enhanced_format(
    mock_context_class,
    mock_connect,
    mock_history,
    mock_workflow,
    temp_bootstrap_config,
    capsys,
):
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

    # Verify enhanced import was called with different parameter sets
    calls = mock_dataset._import_from_url.call_args_list
    assert len(calls) == 3

    # Check that different parameter combinations were used
    assert calls[0][1]['file_name'] == "file1.fastq"  # URL only
    assert calls[1][1]['file_name'] == "custom_file2"  # Custom name
    assert calls[2][1]['file_name'] == "custom_file3"  # Custom name + datatype
    assert calls[2][1]['file_type'] == "fastqsanger"


# Tests for issue #346: v1 history entries may be {url, name} dicts.


def test_normalize_history_entry_string():
    """A plain URL string yields (url, <filename from url>)."""
    from abm.lib.config import _normalize_history_entry

    assert _normalize_history_entry("https://example.com/history.tar.gz") == (
        "https://example.com/history.tar.gz",
        "history.tar.gz",
    )


def test_normalize_history_entry_dict_with_name():
    """A {url, name} dict yields (url, name)."""
    from abm.lib.config import _normalize_history_entry

    entry = {"url": "https://example.com/history.tar.gz", "name": "Variant Test"}
    assert _normalize_history_entry(entry) == (
        "https://example.com/history.tar.gz",
        "Variant Test",
    )


def test_normalize_history_entry_dict_without_name():
    """A dict with only a url yields (url, None)."""
    from abm.lib.config import _normalize_history_entry

    entry = {"url": "https://example.com/history.tar.gz"}
    assert _normalize_history_entry(entry) == (
        "https://example.com/history.tar.gz",
        None,
    )


def test_normalize_history_entry_dict_missing_url():
    """A dict without a url yields (None, ...) so the caller can report the error."""
    from abm.lib.config import _normalize_history_entry

    url, name = _normalize_history_entry({"name": "No URL"})
    assert url is None


@pytest.fixture
def temp_history_bootstrap_config():
    """Bootstrap configs exercising v1 history entries (string and {url, name} dict)."""
    configs = {}

    # v1 with a {url, name} dict history entry -- the case that triggered issue #346
    v1_dict = {
        "version": 1,
        "histories": [
            {
                "url": "https://example.com/Galaxy-History-VC-Test-Data.tar.gz",
                "name": "Variant Test",
            }
        ],
    }

    # v1 with a plain URL string history entry (backward compatibility)
    v1_string = {
        "version": 1,
        "histories": ["https://example.com/plain-history.tar.gz"],
    }

    for key, config in [("dict", v1_dict), ("string", v1_string)]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            configs[key] = f.name

    yield configs

    for config_file in configs.values():
        os.unlink(config_file)


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_history_dict_entry_extracts_url(
    mock_context_class,
    mock_connect,
    mock_history,
    mock_workflow,
    temp_history_bootstrap_config,
    capsys,
):
    """A v1 {url, name} history entry must import the URL string, not the dict (issue #346)."""
    mock_context_class.return_value = MagicMock()
    mock_connect.return_value = MagicMock()

    context = Context('server', 'key', 'kubeconfig')
    with patch('abm.lib.config.dataset'):
        bootstrap(context, ['test_server', temp_history_bootstrap_config['dict']])

    mock_history._import.assert_called_once()
    args, kwargs = mock_history._import.call_args
    # The second positional arg is the args list forwarded to history._import;
    # it must contain the URL string, never the whole {url, name} dict.
    assert args[1] == ["https://example.com/Galaxy-History-VC-Test-Data.tar.gz"]
    # The name from the entry should be forwarded so the history can be renamed.
    assert kwargs.get('name') == "Variant Test"


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_history_string_entry_still_works(
    mock_context_class,
    mock_connect,
    mock_history,
    mock_workflow,
    temp_history_bootstrap_config,
    capsys,
):
    """A plain URL string history entry must still import unchanged (backward compatibility)."""
    mock_context_class.return_value = MagicMock()
    mock_connect.return_value = MagicMock()

    context = Context('server', 'key', 'kubeconfig')
    with patch('abm.lib.config.dataset'):
        bootstrap(context, ['test_server', temp_history_bootstrap_config['string']])

    mock_history._import.assert_called_once()
    args, kwargs = mock_history._import.call_args
    assert args[1] == ["https://example.com/plain-history.tar.gz"]
    # A plain URL string derives its history name from the filename portion.
    assert kwargs.get('name') == "plain-history.tar.gz"


# Tests for issue #349: unified, version-agnostic _process_datasets.


def _fresh_gi(existing_histories=None):
    """Mock GalaxyInstance: get_histories returns existing_histories (default none)."""
    gi = MagicMock()
    gi.histories.get_histories.return_value = existing_histories or []
    gi.histories.create_history.return_value = {'id': 'new_history_id'}
    return gi


def test_normalize_datasets_config_list():
    """A bare list is imported into the default history."""
    from abm.lib.config import DEFAULT_DATASET_HISTORY, _normalize_datasets_config

    urls = ["https://example.com/a.fastq", "https://example.com/b.fastq"]
    assert _normalize_datasets_config(urls) == {DEFAULT_DATASET_HISTORY: urls}


def test_normalize_datasets_config_single_string():
    """A single URL string becomes a one-item default-history list."""
    from abm.lib.config import DEFAULT_DATASET_HISTORY, _normalize_datasets_config

    assert _normalize_datasets_config("https://example.com/a.fastq") == {
        DEFAULT_DATASET_HISTORY: ["https://example.com/a.fastq"]
    }


def test_normalize_datasets_config_single_dataset_dict():
    """A single {url, ...} dict (has a 'url' key) is one default-history item."""
    from abm.lib.config import DEFAULT_DATASET_HISTORY, _normalize_datasets_config

    entry = {"url": "https://example.com/a.fastq", "name": "custom"}
    assert _normalize_datasets_config(entry) == {DEFAULT_DATASET_HISTORY: [entry]}


def test_normalize_datasets_config_history_map_of_lists():
    """A history_name -> list dict passes through unchanged."""
    from abm.lib.config import _normalize_datasets_config

    cfg = {"H1": ["https://example.com/a"], "H2": ["https://example.com/b"]}
    assert _normalize_datasets_config(cfg) == cfg


def test_normalize_datasets_config_history_map_scalar_values():
    """History-map values that are scalars are wrapped in a list."""
    from abm.lib.config import _normalize_datasets_config

    cfg = {
        "H1": "https://example.com/a",
        "H2": {"url": "https://example.com/b", "name": "b"},
    }
    assert _normalize_datasets_config(cfg) == {
        "H1": ["https://example.com/a"],
        "H2": [{"url": "https://example.com/b", "name": "b"}],
    }


def test_normalize_datasets_config_invalid_type(capsys):
    """An unsupported top-level type yields an empty mapping and an error."""
    from abm.lib.config import _normalize_datasets_config

    assert _normalize_datasets_config(123) == {}
    assert "ERROR" in capsys.readouterr().out


@patch('abm.lib.config.dataset')
def test_process_datasets_v0_list(mock_dataset):
    """v0: a list of URLs imports into the default history with a derived name."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(gi, ["https://example.com/a.fastq", "https://example.com/b.bam"])

    gi.histories.create_history.assert_called_once()
    calls = mock_dataset._import_from_url.call_args_list
    assert len(calls) == 2
    # Uniform behavior: bare URLs now pass a derived file_name.
    assert calls[0][1]['file_name'] == "a.fastq"
    assert calls[1][1]['file_name'] == "b.bam"


@patch('abm.lib.config.dataset')
def test_process_datasets_v0_dict(mock_dataset):
    """v0: a history_name -> [urls] dict imports into that history."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(gi, {"My History": ["https://example.com/a.fastq"]})

    gi.histories.create_history.assert_called_once_with(name="My History")
    assert mock_dataset._import_from_url.call_count == 1


@patch('abm.lib.config.dataset')
def test_process_datasets_v1_list_mixed_items(mock_dataset):
    """v1: list items may be strings or {url, name, datatype} dicts."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            "https://example.com/file1.fastq",
            {"url": "https://example.com/file2.fastq", "name": "custom_file2"},
            {
                "url": "https://example.com/file3.fastq",
                "name": "custom_file3",
                "datatype": "fastqsanger",
            },
        ],
    )

    calls = mock_dataset._import_from_url.call_args_list
    assert len(calls) == 3
    assert calls[0][1]['file_name'] == "file1.fastq"
    assert calls[1][1]['file_name'] == "custom_file2"
    assert calls[2][1]['file_name'] == "custom_file3"
    assert calls[2][1]['file_type'] == "fastqsanger"


@patch('abm.lib.config.dataset')
def test_process_datasets_reuses_existing_history(mock_dataset):
    """An existing history is reused rather than recreated."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi(existing_histories=[{'id': 'existing_id', 'name': 'My History'}])
    _process_datasets(gi, {"My History": ["https://example.com/a.fastq"]})

    gi.histories.create_history.assert_not_called()
    assert mock_dataset._import_from_url.call_args[0][1] == 'existing_id'


@patch('abm.lib.config.dataset')
def test_process_datasets_missing_url_reports_and_skips(mock_dataset, capsys):
    """A dict item without a url is reported and skipped, others still import."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(gi, [{"name": "no url"}, "https://example.com/ok.fastq"])

    out = capsys.readouterr().out
    assert "missing required 'url'" in out
    assert mock_dataset._import_from_url.call_count == 1


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
@patch('abm.lib.config.connect')
@patch('abm.lib.config.Context')
def test_bootstrap_ignores_version(
    mock_context_class, mock_connect, mock_history, mock_workflow, capsys
):
    """A config with an arbitrary 'version' still processes datasets normally."""
    mock_context_class.return_value = MagicMock()
    mock_connect.return_value = _fresh_gi()

    config = {"version": 99, "datasets": ["https://example.com/a.fastq"]}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config, f)
        config_file = f.name

    try:
        context = Context('server', 'key', 'kubeconfig')
        with patch('abm.lib.config.dataset') as mock_dataset:
            bootstrap(context, ['test_server', config_file])
        out = capsys.readouterr().out
        assert "unsupported configuration version" not in out
        assert mock_dataset._import_from_url.call_count == 1
    finally:
        os.unlink(config_file)


# Tests for issue #354: `config create --master`.


@patch('abm.lib.config.save_profiles')
@patch('abm.lib.config.load_profiles')
def test_config_create_with_master(mock_load, mock_save):
    """--master stores the master (bootstrap) key in the new profile."""
    mock_load.return_value = {}
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['prof', '--url', 'http://x', '--master', 'MASTER_KEY'])

    saved = mock_save.call_args[0][0]
    assert saved['prof']['master'] == 'MASTER_KEY'
    assert saved['prof']['url'] == 'http://x'


@patch('abm.lib.config.save_profiles')
@patch('abm.lib.config.load_profiles')
def test_config_create_without_master_omits_field(mock_load, mock_save):
    """Without --master no 'master' field is written, preserving key fallback."""
    mock_load.return_value = {}
    context = Context('server', 'key', 'kubeconfig')

    create(context, ['prof', '--url', 'http://x'])

    saved = mock_save.call_args[0][0]
    assert 'master' not in saved['prof']


# Tests for issue #364: dataset collections in the bootstrap 'datasets' section.


def _upload_side_effect(prefix='ds'):
    """Build a fake put_url response per call, with ids ds1, ds2, ..."""
    counter = {'n': 0}

    def _put(gi, history_id, url, **kwargs):
        counter['n'] += 1
        return {'outputs': [{'id': f"{prefix}{counter['n']}", 'name': url}]}

    return _put


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_returns_dataset_id(mock_dataset):
    """The id of the new dataset is returned so callers can build collections."""
    mock_dataset._import_from_url.return_value = {'outputs': [{'id': 'abc123'}]}
    gi = MagicMock()

    result = _import_dataset_with_metadata(gi, 'hid', 'https://example.com/a.fastq')

    assert result == 'abc123'


@patch('abm.lib.config.dataset')
def test_import_dataset_with_metadata_invalid_returns_none(mock_dataset):
    """An invalid config yields None rather than an id."""
    gi = MagicMock()

    assert _import_dataset_with_metadata(gi, 'hid', {'name': 'no url'}) is None
    assert _import_dataset_with_metadata(gi, 'hid', 42) is None


@patch('abm.lib.config.dataset')
def test_process_datasets_list_collection(mock_dataset):
    """A list collection uploads each leaf and creates one collection from the ids."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    _process_datasets(
        gi,
        {
            "H": [
                {
                    'collection': 'controls',
                    'type': 'list',
                    'elements': {
                        'ctrl1': 'https://example.com/ctrl1.fastq.gz',
                        'ctrl2': {
                            'url': 'https://example.com/ctrl2.fastq.gz',
                            'datatype': 'fastqsanger.gz',
                        },
                    },
                }
            ]
        },
    )

    calls = mock_dataset._import_from_url.call_args_list
    assert len(calls) == 2
    # Names default to the element identifier when the leaf has no name.
    assert calls[0].kwargs['file_name'] == 'ctrl1'
    assert calls[1].kwargs['file_name'] == 'ctrl2'
    assert calls[1].kwargs['file_type'] == 'fastqsanger.gz'

    gi.histories.create_dataset_collection.assert_called_once()
    kwargs = gi.histories.create_dataset_collection.call_args.kwargs
    assert kwargs['history_id'] == 'new_history_id'
    description = kwargs['collection_description'].to_dict()
    assert description['name'] == 'controls'
    assert description['collection_type'] == 'list'
    assert [e['name'] for e in description['element_identifiers']] == [
        'ctrl1',
        'ctrl2',
    ]
    assert [e['id'] for e in description['element_identifiers']] == ['ds1', 'ds2']


@patch('abm.lib.config.dataset')
def test_process_datasets_list_paired_collection(mock_dataset):
    """A list:paired collection builds paired elements with forward/reverse ids."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            {
                'collection': 'wt_H3K4me3',
                'type': 'list:paired',
                'elements': {
                    'pair1': {
                        'forward': 'https://example.com/r1.fastq.gz',
                        'reverse': 'https://example.com/r2.fastq.gz',
                    },
                    'pair2': {
                        'forward': {
                            'url': 'https://example.com/rep2_R1.fastq.gz',
                            'name': 'rep2_fwd',
                        },
                        'reverse': {'url': 'https://example.com/rep2_R2.fastq.gz'},
                    },
                },
            }
        ],
    )

    calls = mock_dataset._import_from_url.call_args_list
    assert [c.kwargs['file_name'] for c in calls] == [
        'pair1_forward',
        'pair1_reverse',
        'rep2_fwd',
        'pair2_reverse',
    ]

    description = gi.histories.create_dataset_collection.call_args.kwargs[
        'collection_description'
    ].to_dict()
    assert description['collection_type'] == 'list:paired'
    pairs = description['element_identifiers']
    assert [p['name'] for p in pairs] == ['pair1', 'pair2']
    assert pairs[0]['collection_type'] == 'paired'
    assert [e['name'] for e in pairs[0]['element_identifiers']] == [
        'forward',
        'reverse',
    ]
    assert [e['id'] for e in pairs[0]['element_identifiers']] == ['ds1', 'ds2']
    assert [e['id'] for e in pairs[1]['element_identifiers']] == ['ds3', 'ds4']


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_hide_elements(mock_dataset):
    """hide_elements: true hides each member dataset after the collection exists."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            {
                'collection': 'c',
                'type': 'list',
                'hide_elements': True,
                'elements': {'a': 'https://example.com/a', 'b': 'https://example.com/b'},
            }
        ],
    )

    hidden = [c.args[1] for c in gi.histories.update_dataset.call_args_list]
    assert sorted(hidden) == ['ds1', 'ds2']
    for c in gi.histories.update_dataset.call_args_list:
        assert c.kwargs == {'visible': False}


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_elements_visible_by_default(mock_dataset):
    """Without hide_elements the member datasets are left visible."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    _process_datasets(
        gi,
        [{'collection': 'c', 'type': 'list', 'elements': {'a': 'https://x/a'}}],
    )

    gi.histories.update_dataset.assert_not_called()


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_unknown_type_skipped(mock_dataset, capsys):
    """An unknown collection type is reported; nothing is uploaded or created."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            {'collection': 'bad', 'type': 'list:list', 'elements': {'a': 'https://x/a'}},
            'https://example.com/ok.fastq',
        ],
    )

    out = capsys.readouterr().out
    assert "ERROR" in out and "list:list" in out
    gi.histories.create_dataset_collection.assert_not_called()
    # The plain dataset after the bad collection is still imported.
    assert mock_dataset._import_from_url.call_count == 1


@patch('abm.lib.config.dataset')
def test_process_datasets_paired_element_missing_reverse_skipped(
    mock_dataset, capsys
):
    """A list:paired element without forward and reverse skips the collection."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            {
                'collection': 'c',
                'type': 'list:paired',
                'elements': {
                    'pair1': {'forward': 'https://x/r1'},
                },
            }
        ],
    )

    out = capsys.readouterr().out
    assert "ERROR" in out and "reverse" in out
    mock_dataset._import_from_url.assert_not_called()
    gi.histories.create_dataset_collection.assert_not_called()


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_missing_elements_skipped(mock_dataset, capsys):
    """A collection with no elements mapping is reported and skipped."""
    from abm.lib.config import _process_datasets

    gi = _fresh_gi()
    _process_datasets(gi, [{'collection': 'c', 'type': 'list'}])

    out = capsys.readouterr().out
    assert "ERROR" in out and "elements" in out
    gi.histories.create_dataset_collection.assert_not_called()


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_failed_leaf_upload_skipped(
    mock_dataset, capsys
):
    """A leaf upload that raises skips the collection without aborting bootstrap."""
    from abm.lib.config import _process_datasets

    responses = iter(
        [
            {'outputs': [{'id': 'ds1'}]},
            RuntimeError('boom'),
            {'outputs': [{'id': 'ds3'}]},
        ]
    )

    def _put(*args, **kwargs):
        r = next(responses)
        if isinstance(r, Exception):
            raise r
        return r

    mock_dataset._import_from_url.side_effect = _put
    gi = _fresh_gi()
    _process_datasets(
        gi,
        [
            {
                'collection': 'c',
                'type': 'list',
                'elements': {'a': 'https://x/a', 'b': 'https://x/b'},
            },
            'https://example.com/after.fastq',
        ],
    )

    out = capsys.readouterr().out
    assert "ERROR" in out and "boom" in out
    gi.histories.create_dataset_collection.assert_not_called()
    # The dataset listed after the failed collection is still imported.
    assert mock_dataset._import_from_url.call_count == 3


@patch('abm.lib.config.dataset')
def test_process_datasets_collection_create_failure_reported(mock_dataset, capsys):
    """An error from Galaxy while creating the collection is reported, not raised."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    gi.histories.create_dataset_collection.side_effect = RuntimeError('galaxy said no')
    _process_datasets(
        gi,
        [{'collection': 'c', 'type': 'list', 'elements': {'a': 'https://x/a'}}],
    )

    out = capsys.readouterr().out
    assert "ERROR" in out and "galaxy said no" in out


@patch('abm.lib.config.dataset')
def test_process_datasets_mixed_datasets_and_collections(mock_dataset):
    """Plain datasets and collections can be mixed in one history list."""
    from abm.lib.config import _process_datasets

    mock_dataset._import_from_url.side_effect = _upload_side_effect()
    gi = _fresh_gi()
    _process_datasets(
        gi,
        {
            "H": [
                {'url': 'https://example.com/reference.fasta', 'name': 'reference'},
                {'collection': 'c', 'type': 'list', 'elements': {'a': 'https://x/a'}},
            ]
        },
    )

    assert mock_dataset._import_from_url.call_count == 2
    gi.histories.create_dataset_collection.assert_called_once()
