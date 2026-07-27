from unittest.mock import MagicMock, patch

from abm.lib.history import _import


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
