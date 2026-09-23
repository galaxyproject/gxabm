"""Tests for the Terra workspace ``bootstrap:`` folder import and ``failOnImport``."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml

from abm.lib.common import Context
from abm.lib.config import (
    DEFAULT_TERRA_FILE_SOURCE,
    BootstrapResult,
    _bootstrap_folder_candidates,
    _classify_bootstrap_file,
    _list_remote_files,
    _process_terra_bootstrap,
    _process_terra_workspaces,
    bootstrap,
)

ROOT = f"gxfiles://{DEFAULT_TERRA_FILE_SOURCE}"
FOLDER = f"{ROOT}/Other Data/Files/galaxy-bootstrap"


def _response(status=200, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload if payload is not None else []
    return r


def _entry(name, cls='File', folder=FOLDER):
    return {'class': cls, 'name': name, 'uri': f"{folder}/{name}"}


def _gi(listing=None, status=200):
    gi = MagicMock()
    gi.url = 'http://galaxy/api'
    gi.make_get_request.return_value = _response(status, listing)
    gi.workflows._post.return_value = {'id': 'wf1', 'name': 'wf'}
    return gi


@pytest.fixture
def config_file():
    """Write a bootstrap config dict to a temp file; yields a writer function."""
    paths = []

    def write(config):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config, f)
            paths.append(f.name)
        return f.name

    yield write
    for p in paths:
        os.unlink(p)


# --- classification -------------------------------------------------------


@pytest.mark.parametrize(
    'name,expected',
    [
        ('rnaseq.ga', 'workflow'),
        ('RNASEQ.GA', 'workflow'),
        ('history.rocrate.zip', 'history'),
        ('history.tar.gz', 'history'),
        ('history.tgz', 'history'),
        ('history.tar', 'history'),
        ('reads.fastq.gz', None),
        ('archive.zip', None),
        ('README.md', None),
    ],
)
def test_classify_bootstrap_file(name, expected):
    assert _classify_bootstrap_file(name) == expected


def test_bootstrap_folder_candidates_bare_name_tries_bucket_first():
    assert _bootstrap_folder_candidates('galaxy-bootstrap') == [
        'Other Data/Files/galaxy-bootstrap',
        'galaxy-bootstrap',
    ]


def test_bootstrap_folder_candidates_path_is_literal():
    assert _bootstrap_folder_candidates('/Other Data/Files/a/b/') == [
        'Other Data/Files/a/b'
    ]


# --- listing --------------------------------------------------------------


def test_list_remote_files_returns_entries():
    gi = _gi([_entry('a.ga')])
    assert _list_remote_files(gi, FOLDER) == [_entry('a.ga')]
    url = gi.make_get_request.call_args[0][0]
    params = gi.make_get_request.call_args[1]['params']
    assert url == 'http://galaxy/api/remote_files'
    assert params['target'] == FOLDER
    assert params['recursive'] == 'true'


def test_list_remote_files_missing_returns_none():
    assert _list_remote_files(_gi(status=404), FOLDER) is None


def test_list_remote_files_exception_returns_none():
    gi = _gi()
    gi.make_get_request.side_effect = Exception('boom')
    assert _list_remote_files(gi, FOLDER) is None


# --- folder import --------------------------------------------------------


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
def test_terra_bootstrap_imports_histories_and_workflows(
    mock_history, mock_workflow, capsys
):
    mock_history._do_import.return_value = 'new_history'
    gi = _gi(
        [
            _entry('sub', cls='Directory'),
            _entry('wf.ga'),
            _entry('h.rocrate.zip'),
            _entry('h2.tar.gz'),
            _entry('notes.txt'),
        ]
    )
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)

    imported = [c[0][1] for c in mock_history._do_import.call_args_list]
    assert imported == [f"{FOLDER}/h.rocrate.zip", f"{FOLDER}/h2.tar.gz"]
    gi.workflows._post.assert_called_once_with(
        payload={'archive_source': f"{FOLDER}/wf.ga"}
    )
    gi.workflows.update_workflow.assert_called_once_with('wf1', published=True)
    assert (result.imported, result.failed) == (3, 0)
    assert 'notes.txt' in capsys.readouterr().out


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
def test_terra_bootstrap_installs_tools_after_import(mock_history, mock_workflow):
    gi = _gi([_entry('wf.ga')])
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)
    mock_workflow.install_tools_for_workflow.assert_called_once_with(gi, 'wf1')
    assert (result.imported, result.failed) == (1, 0)


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
def test_terra_bootstrap_tool_install_failure_does_not_fail_import(
    mock_history, mock_workflow
):
    mock_workflow.install_tools_for_workflow.return_value = False
    mock_history._do_import.return_value = 'hid'
    gi = _gi([_entry('wf.ga'), _entry('h.tar.gz')])
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)
    # both items imported; the history after the workflow's tool problem
    assert (result.imported, result.failed) == (2, 0)
    mock_history._do_import.assert_called_once()


@patch('abm.lib.config.history')
def test_terra_bootstrap_missing_folder_is_not_a_failure(mock_history, capsys):
    gi = _gi(status=404)
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)

    assert (result.imported, result.failed) == (0, 0)
    mock_history._do_import.assert_not_called()
    out = capsys.readouterr().out
    assert 'ERROR' not in out
    assert 'galaxy-bootstrap' in out


@patch('abm.lib.config.history')
def test_terra_bootstrap_falls_back_to_literal_path(mock_history):
    gi = _gi()
    literal = f"{ROOT}/galaxy-bootstrap"
    gi.make_get_request.side_effect = [
        _response(404),
        _response(200, [_entry('h.tar.gz', folder=literal)]),
    ]
    mock_history._do_import.return_value = 'hid'
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)

    targets = [c[1]['params']['target'] for c in gi.make_get_request.call_args_list]
    assert targets == [FOLDER, literal]
    assert result.imported == 1


@patch('abm.lib.config.history')
def test_terra_bootstrap_custom_file_source(mock_history):
    gi = _gi([])
    _process_terra_bootstrap(
        gi, {'bootstrap': 'a/b', 'file_source': 'other-ws'}, BootstrapResult()
    )
    target = gi.make_get_request.call_args[1]['params']['target']
    assert target == 'gxfiles://other-ws/a/b'


@patch('abm.lib.config.workflow')
@patch('abm.lib.config.history')
def test_terra_bootstrap_counts_failures(mock_history, mock_workflow):
    mock_history._do_import.side_effect = [None, Exception('boom'), 'hid']
    gi = _gi(
        [
            _entry('a.tar.gz'),
            _entry('b.tar.gz'),
            _entry('c.tar.gz'),
            _entry('bad.ga'),
        ]
    )
    gi.workflows._post.side_effect = Exception('import failed')
    result = BootstrapResult()
    _process_terra_bootstrap(gi, {'bootstrap': 'galaxy-bootstrap'}, result)
    assert (result.imported, result.failed) == (1, 3)


# --- terra section --------------------------------------------------------


@patch('abm.lib.config._process_terra_bootstrap')
def test_terra_entry_with_only_bootstrap_does_not_need_anvilfs(mock_boot):
    """namespace/workspace are optional when an entry only has `bootstrap`."""
    gi = _gi()
    result = BootstrapResult()
    with patch('abm.lib.config.TERRA_AVAILABLE', False):
        _process_terra_workspaces(gi, [{'bootstrap': 'galaxy-bootstrap'}], result)
    mock_boot.assert_called_once()
    assert result.failed == 0


@patch('abm.lib.config._process_terra_bootstrap')
def test_terra_section_accepts_single_mapping(mock_boot):
    _process_terra_workspaces(_gi(), {'bootstrap': 'galaxy-bootstrap'})
    mock_boot.assert_called_once()


@patch('abm.lib.config._process_terra_bootstrap')
def test_terra_entry_with_datasets_still_requires_namespace(mock_boot, capsys):
    result = BootstrapResult()
    _process_terra_workspaces(
        _gi(), [{'datasets': {'H': ['*.fastq']}, 'bootstrap': 'b'}], result
    )
    assert "missing 'namespace' or 'workspace'" in capsys.readouterr().out
    assert result.failed == 1
    # the bootstrap folder is still processed
    mock_boot.assert_called_once()


@patch('abm.lib.config._process_terra_bootstrap')
def test_terra_existing_datasets_format_unchanged(mock_boot):
    """An existing-format entry still drives the AnVILFS dataset import."""
    gi = _gi()
    gi.histories.get_histories.return_value = [{'id': 'h1'}]
    file_info = MagicMock(is_file=True, size=1)
    file_info.name = 'a.fastq'
    fs = MagicMock()
    fs.scandir.return_value = [file_info]
    entry = {
        'namespace': 'ns',
        'workspace': 'ws',
        'datasets': {'H': [{'pattern': 'Tables/sample/*.fastq'}]},
    }
    result = BootstrapResult()
    with (
        patch('abm.lib.config.TERRA_AVAILABLE', True),
        patch('abm.lib.config.AnVILFS', return_value=fs, create=True),
        patch('abm.lib.config.dataset') as mock_dataset,
    ):
        _process_terra_workspaces(gi, [entry], result)

    fs.scandir.assert_called_once_with('Tables/sample')
    assert mock_dataset._import_from_url.call_count == 1
    assert (result.imported, result.failed) == (1, 0)
    mock_boot.assert_not_called()


# --- failOnImport ---------------------------------------------------------


def _run_bootstrap(config_path, history_result='hid', workflow_result=True):
    with (
        patch('abm.lib.config.Context'),
        patch('abm.lib.config.connect', return_value=_gi()),
        patch('abm.lib.config.history') as mock_history,
        patch('abm.lib.config.workflow') as mock_workflow,
        patch('abm.lib.config.dataset'),
    ):
        mock_history._import.return_value = history_result
        mock_workflow.import_from_url.return_value = workflow_result
        bootstrap(Context('server', 'key', 'kube'), ['server', config_path])


def test_fail_on_import_default_only_logs(config_file, capsys):
    path = config_file({'histories': ['https://example.com/h.tar.gz']})
    _run_bootstrap(path, history_result=None)  # must not raise SystemExit
    assert 'failed 1' in capsys.readouterr().out


def test_fail_on_import_false_only_logs(config_file):
    path = config_file(
        {'failOnImport': False, 'histories': ['https://example.com/h.tar.gz']}
    )
    _run_bootstrap(path, history_result=None)


def test_fail_on_import_success_exits_zero(config_file, capsys):
    path = config_file(
        {'failOnImport': True, 'histories': ['https://example.com/h.tar.gz']}
    )
    _run_bootstrap(path)
    assert 'Imported 1, failed 0' in capsys.readouterr().out


@pytest.mark.parametrize(
    'section',
    [
        {'histories': ['https://example.com/h.tar.gz']},
        {'histories': [{'name': 'no url'}]},
        {'datasets': [{'name': 'no url'}]},
        {'workflows': ['https://example.com/wf.ga']},
        {'workflows-no-tools': ['https://example.com/wf.ga']},
        {'terra': [{'datasets': {'H': ['*.fastq']}}]},
    ],
    ids=[
        'history',
        'history-no-url',
        'dataset',
        'workflow',
        'workflow-no-tools',
        'terra',
    ],
)
def test_fail_on_import_true_exits_nonzero(config_file, section):
    path = config_file({'failOnImport': True, **section})
    with pytest.raises(SystemExit) as e:
        _run_bootstrap(path, history_result=None, workflow_result=False)
    assert e.value.code == 1


def test_fail_on_import_dataset_exception(config_file):
    path = config_file(
        {'failOnImport': True, 'datasets': ['https://example.com/a.fastq']}
    )
    with (
        patch('abm.lib.config.Context'),
        patch('abm.lib.config.connect', return_value=_gi()),
        patch('abm.lib.config.dataset') as mock_dataset,
    ):
        mock_dataset._import_from_url.side_effect = Exception('boom')
        with pytest.raises(SystemExit):
            bootstrap(Context('server', 'key', 'kube'), ['server', path])


# --- tool installation ----------------------------------------------------


def test_install_tools_never_raises(tmp_path):
    from abm.lib import workflow as wf

    path = tmp_path / 'w.ga'
    path.write_text('{}')
    with patch.object(wf, 'install_shed_repos', side_effect=Exception('shed down')):
        assert wf.install_tools(MagicMock(), str(path)) is False


def test_install_tools_ignores_failed_repositories(tmp_path):
    """Failed repositories are warned about (ignore_dependency_problems=True), not raised."""
    from abm.lib import workflow as wf

    path = tmp_path / 'w.ga'
    path.write_text('{}')
    with patch.object(wf, 'install_shed_repos', return_value=([], None)) as shed:
        assert wf.install_tools(MagicMock(), str(path)) is True
    assert shed.call_args[0][2] is True


def test_install_tools_for_workflow_exports_then_installs(tmp_path):
    from abm.lib import workflow as wf

    gi = MagicMock()
    gi.workflows.export_workflow_dict.return_value = {'name': 'w', 'steps': {}}
    with (
        patch.object(wf, 'WORKFLOW_CACHE', str(tmp_path)),
        patch.object(wf, 'install_tools', return_value=True) as install,
    ):
        assert wf.install_tools_for_workflow(gi, 'abc') is True
    install.assert_called_once_with(gi, str(tmp_path / 'abc.ga'))
    assert (tmp_path / 'abc.ga').read_text() == '{"name": "w", "steps": {}}'


def test_install_tools_for_workflow_export_failure(tmp_path):
    from abm.lib import workflow as wf

    gi = MagicMock()
    gi.workflows.export_workflow_dict.side_effect = Exception('nope')
    with patch.object(wf, 'WORKFLOW_CACHE', str(tmp_path)):
        assert wf.install_tools_for_workflow(gi, 'abc') is False
