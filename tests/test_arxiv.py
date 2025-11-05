from unittest import mock

from arxiv_sanity_bot.arxiv.arxiv_abstracts import (
    get_all_abstracts,
    _extract_arxiv_id,
    get_url,
    _fetch_from_arxiv,
    ArxivZeroResultsError,
)
import pandas as pd
import arxiv
from unittest.mock import Mock, patch, MagicMock
import pytest
from datetime import datetime, timezone

from arxiv_sanity_bot.sanitize_text import sanitize_text


@pytest.fixture
def mock_arxiv_client():
    with patch("arxiv.Client") as mock_client:
        yield mock_client


def test_extract_arxiv_id():
    assert _extract_arxiv_id("http://arxiv.org/abs/0000.00000") == "0000.00000"
    assert _extract_arxiv_id("http://arxiv.org/abs/0000.00000v1") == "0000.00000"
    assert _extract_arxiv_id("http://arxiv.org/abs/0000.00000v99") == "0000.00000"
    assert _extract_arxiv_id("https://arxiv.org/abs/0000.00000v99") == "0000.00000"
    assert _extract_arxiv_id("http://arxiv.org/abs/9999.99v99") == "9999.99"
    assert _extract_arxiv_id("http://arxiv.org/abs/99.99") == "99.99"


def test_get_url():
    arxiv_id = "2101.12345"
    expected_url = "https://arxiv.org/abs/2101.12345"

    assert get_url(arxiv_id) == expected_url


def test_get_all_abstracts():
    after = datetime(2024, 1, 1, tzinfo=timezone.utc)
    before = datetime(2024, 1, 2, tzinfo=timezone.utc)

    mock_rows = [
        {
            'arxiv': '2401.00001',
            'title': 'Test Paper 1',
            'abstract': 'Test abstract 1',
            'published_on': '2024-01-01T10:00:00Z',
            'categories': ['cs.LG']
        },
        {
            'arxiv': '2401.00002',
            'title': 'Test Paper 2',
            'abstract': 'Test abstract 2',
            'published_on': '2024-01-01T15:00:00Z',
            'categories': ['cs.CV']
        }
    ]

    with patch('arxiv_sanity_bot.arxiv.arxiv_abstracts._fetch_from_arxiv', return_value=mock_rows), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts._fetch_scores', return_value=pd.DataFrame({
             'arxiv': ['2401.00001', '2401.00002'],
             'score': [0.8, 0.9]
         })):

        result = get_all_abstracts(after, before)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'arxiv' in result.columns
        assert 'title' in result.columns
        assert 'abstract' in result.columns
        assert 'published_on' in result.columns
        assert 'score' in result.columns

        assert result.iloc[0]['score'] >= result.iloc[1]['score']

        assert pd.api.types.is_datetime64_any_dtype(result['published_on'])


def test_fetch_from_arxiv_retries_on_zero_results():
    after = datetime(2024, 1, 1, tzinfo=timezone.utc)
    before = datetime(2024, 1, 2, tzinfo=timezone.utc)

    empty_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>ArXiv Query</title>
    </feed>'''

    xml_with_entry = '''<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
        <entry>
            <id>http://arxiv.org/abs/2401.00001v1</id>
            <title>Test Paper</title>
            <summary>Test abstract</summary>
            <published>2024-01-01T10:00:00Z</published>
            <arxiv:primary_category term="cs.LG"/>
        </entry>
    </feed>'''

    mock_response_empty = Mock()
    mock_response_empty.content = empty_xml.encode('utf-8')
    mock_response_empty.raise_for_status = Mock()

    mock_response_with_data = Mock()
    mock_response_with_data.content = xml_with_entry.encode('utf-8')
    mock_response_with_data.raise_for_status = Mock()

    with patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.requests.get') as mock_get, \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.time.sleep') as mock_sleep, \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.RetryableErrorEvent') as mock_retry_event:

        mock_get.side_effect = [mock_response_empty, mock_response_with_data]

        result = _fetch_from_arxiv(after, before, max_results=1000)

        assert len(result) == 1
        assert result[0]['arxiv'] == '2401.00001'
        assert result[0]['title'] == 'Test Paper'

        assert mock_get.call_count == 2
        mock_retry_event.assert_called_once()
        mock_sleep.assert_called_once()


def test_fetch_from_arxiv_raises_after_max_retries():
    after = datetime(2024, 1, 1, tzinfo=timezone.utc)
    before = datetime(2024, 1, 2, tzinfo=timezone.utc)

    empty_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>ArXiv Query</title>
    </feed>'''

    mock_response = Mock()
    mock_response.content = empty_xml.encode('utf-8')
    mock_response.raise_for_status = Mock()

    with patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.requests.get', return_value=mock_response), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.time.sleep'), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.RetryableErrorEvent'), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.ARXIV_ZERO_RESULTS_MAX_RETRIES', 3):

        with pytest.raises(ArxivZeroResultsError):
            _fetch_from_arxiv(after, before, max_results=1000)


def test_fetch_from_arxiv_does_not_retry_on_api_errors():
    after = datetime(2024, 1, 1, tzinfo=timezone.utc)
    before = datetime(2024, 1, 2, tzinfo=timezone.utc)

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("API Error")

    with patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.requests.get', return_value=mock_response), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.time.sleep') as mock_sleep, \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts.RetryableErrorEvent'):

        result = _fetch_from_arxiv(after, before, max_results=1000)

        assert result == []
        mock_sleep.assert_not_called()
