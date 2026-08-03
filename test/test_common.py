from unittest.mock import MagicMock

from abm.lib.common import _looks_like_id, find_history


def test_looks_like_id():
    assert _looks_like_id('0123456789abcdef')  # 16 hex chars
    assert _looks_like_id('0123456789abcdef' * 2)  # 32 hex chars
    assert not _looks_like_id('Variant Test')  # space + non-hex
    assert not _looks_like_id('shorthex0')  # not a multiple of 16
    assert not _looks_like_id('')  # empty


def test_find_history_by_name_skips_show_history():
    """A name is resolved via get_histories without probing show_history."""
    gi = MagicMock()
    gi.histories.get_histories.return_value = [
        {'id': '0123456789abcdef', 'name': 'Variant Test'}
    ]

    result = find_history(gi, 'Variant Test')

    assert result == '0123456789abcdef'
    gi.histories.show_history.assert_not_called()
    gi.histories.get_histories.assert_called_once_with(name='Variant Test')


def test_find_history_by_id_uses_show_history():
    """An id-shaped value is resolved via show_history, not get_histories."""
    gi = MagicMock()
    gi.histories.show_history.return_value = {'id': '0123456789abcdef'}

    result = find_history(gi, '0123456789abcdef')

    assert result == '0123456789abcdef'
    gi.histories.show_history.assert_called_once()
    gi.histories.get_histories.assert_not_called()


def test_find_history_name_not_found_returns_none():
    """An unknown name returns None without probing show_history."""
    gi = MagicMock()
    gi.histories.get_histories.return_value = []

    assert find_history(gi, 'No Such History') is None
    gi.histories.show_history.assert_not_called()
