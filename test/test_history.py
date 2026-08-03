from unittest.mock import MagicMock, patch

from abm.lib.history import _import, delete


def _make_gi(before_ids, after_histories):
    """Build a mock GalaxyInstance whose history list grows after the import."""
    gi = MagicMock()
    gi.histories.get_histories.side_effect = [
        [{'id': hid, 'name': hid} for hid in before_ids],
        after_histories,
    ]
    gi.histories.import_history.return_value = {'id': 'import_job_id'}
    return gi


@patch('abm.lib.history.connect')
def test_import_returns_new_history_id(mock_connect):
    """_import returns the id of the history created by the import job."""
    gi = _make_gi(
        before_ids=['h1'],
        after_histories=[{'id': 'h1', 'name': 'h1'}, {'id': 'h2', 'name': 'imported'}],
    )
    mock_connect.return_value = gi

    result = _import(MagicMock(), ['https://example.com/history.tar.gz'])

    assert result == 'h2'
    gi.histories.import_history.assert_called_once_with(
        url='https://example.com/history.tar.gz'
    )
    gi.histories.update_history.assert_not_called()


@patch('abm.lib.history.connect')
def test_import_renames_when_name_given(mock_connect):
    """When a name is supplied the new history is renamed to it."""
    gi = _make_gi(
        before_ids=['h1'],
        after_histories=[{'id': 'h1', 'name': 'h1'}, {'id': 'h2', 'name': 'imported'}],
    )
    mock_connect.return_value = gi

    result = _import(
        MagicMock(), ['https://example.com/history.tar.gz'], name='Variant Test'
    )

    assert result == 'h2'
    gi.histories.update_history.assert_called_once_with('h2', name='Variant Test')


@patch('abm.lib.history.connect')
def test_import_returns_none_when_no_new_history(mock_connect):
    """If no new history appears, _import returns None and does not rename."""
    gi = _make_gi(
        before_ids=['h1'],
        after_histories=[{'id': 'h1', 'name': 'h1'}],
    )
    mock_connect.return_value = gi

    result = _import(MagicMock(), ['https://example.com/history.tar.gz'], name='X')

    assert result is None
    gi.histories.update_history.assert_not_called()


@patch('abm.lib.history.connect')
def test_import_returns_none_when_job_fails(mock_connect):
    """If waiting for the import job raises, _import returns None."""
    gi = MagicMock()
    gi.histories.get_histories.return_value = [{'id': 'h1', 'name': 'h1'}]
    gi.histories.import_history.return_value = {'id': 'import_job_id'}
    gi.jobs.wait_for_job.side_effect = Exception('boom')
    mock_connect.return_value = gi

    result = _import(MagicMock(), ['https://example.com/history.tar.gz'])

    assert result is None
    gi.histories.update_history.assert_not_called()


# Tests for issue #356: delete multiple histories at once.


@patch('abm.lib.history.find_history')
@patch('abm.lib.history.connect')
def test_delete_multiple(mock_connect, mock_find):
    """Multiple identifiers each resolve and get deleted."""
    gi = MagicMock()
    mock_connect.return_value = gi
    mock_find.side_effect = lambda g, ident: {
        'Variant Test': 'id1',
        'Variant 2G': 'id2',
    }[ident]

    delete(MagicMock(), ['Variant Test', 'Variant 2G'])

    deleted = [c.args[0] for c in gi.histories.delete_history.call_args_list]
    assert deleted == ['id1', 'id2']


@patch('abm.lib.history.find_history')
@patch('abm.lib.history.connect')
def test_delete_single(mock_connect, mock_find):
    """A single identifier still deletes as before (backward compatibility)."""
    gi = MagicMock()
    mock_connect.return_value = gi
    mock_find.return_value = 'id1'

    delete(MagicMock(), ['id1'])

    gi.histories.delete_history.assert_called_once_with('id1', True)


@patch('abm.lib.history.find_history')
@patch('abm.lib.history.connect')
def test_delete_skips_missing(mock_connect, mock_find, capsys):
    """A missing history is reported and skipped; others are still deleted."""
    gi = MagicMock()
    mock_connect.return_value = gi
    mock_find.side_effect = [None, 'id2']

    delete(MagicMock(), ['missing', 'good'])

    gi.histories.delete_history.assert_called_once_with('id2', True)
    assert 'No such history' in capsys.readouterr().out


@patch('abm.lib.history.connect')
def test_delete_no_args_errors(mock_connect, capsys):
    """No identifiers prints an error and does not connect/delete."""
    delete(MagicMock(), [])

    assert 'ERROR' in capsys.readouterr().out
    mock_connect.assert_not_called()
