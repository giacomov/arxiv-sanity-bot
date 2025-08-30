from unittest import mock

from arxiv_sanity_bot.arxiv.arxiv_abstracts import (
    get_all_abstracts,
    _extract_arxiv_id,
    get_url,
)
import pandas as pd
import arxiv
from unittest.mock import Mock, patch, MagicMock
import pytest

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
    from datetime import datetime, timezone

    after = datetime(2024, 1, 1, tzinfo=timezone.utc)
    before = datetime(2024, 1, 2, tzinfo=timezone.utc)
    
    # Mock the internal fetch function to return test data
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
    
    # Mock the internal functions
    with patch('arxiv_sanity_bot.arxiv.arxiv_abstracts._fetch_from_arxiv_3', return_value=mock_rows), \
         patch('arxiv_sanity_bot.arxiv.arxiv_abstracts._fetch_scores', return_value=pd.DataFrame({
             'arxiv': ['2401.00001', '2401.00002'], 
             'score': [0.8, 0.9]
         })):
        
        result = get_all_abstracts(after, before)
        
        # Test external functionality
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'arxiv' in result.columns
        assert 'title' in result.columns
        assert 'abstract' in result.columns
        assert 'published_on' in result.columns
        assert 'score' in result.columns
        
        # Check that results are sorted by score (descending)
        assert result.iloc[0]['score'] >= result.iloc[1]['score']
        
        # Check that published_on is datetime
        assert pd.api.types.is_datetime64_any_dtype(result['published_on'])
