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


def test_get_all_abstracts(mock_arxiv_client):
    # Mock the arxiv search results
    mock_entry = Mock()
    mock_entry.entry_id = "https://arxiv.org/abs/2101.12345v2"
    mock_entry.title = "Sample Title"
    mock_entry.summary = "Sample abstract with some & special % characters."
    mock_entry.published = pd.to_datetime("2021-01-01T00:00:00Z")

    mock_result = MagicMock()
    mock_result.__iter__.return_value = [mock_entry]

    mock_arxiv_client.return_value.results.return_value = mock_result

    with mock.patch(
        "arxiv_sanity_bot.arxiv.arxiv_abstracts._fetch_scores"
    ) as mock_fetch_scores:
        mock_fetch_scores.return_value = pd.DataFrame(
            [
                {
                    "arxiv": "2101.12345",
                    "score": 9.0,
                    "published_on": pd.to_datetime("2021-01-01T00:00:00Z"),
                }
            ]
        )

        abstracts = get_all_abstracts(
            max_pages=1, after=pd.to_datetime("2020-12-31T00:00:00Z"), before=pd.to_datetime("2021-12-31T00:00:00Z")
        )

    assert isinstance(abstracts, pd.DataFrame)
    assert len(abstracts) == 1
    assert abstracts.iloc[0]["arxiv"] == "2101.12345"
    assert abstracts.iloc[0]["title"] == "Sample Title"
    assert (
        abstracts.iloc[0]["abstract"] == "Sample abstract with some special characters."
    )


def test_get_url():
    arxiv_id = "2101.12345"
    expected_url = "https://arxiv.org/abs/2101.12345"

    assert get_url(arxiv_id) == expected_url
