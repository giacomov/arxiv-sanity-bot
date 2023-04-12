import pytest
import pandas as pd
from unittest import mock
from datetime import datetime
from arxiv_sanity_bot.arxiv_sanity.abstracts import (
    sanitize_text,
    _extract_arxiv_number,
    get_abstracts_from_page,
    bulk_download,
    get_all_abstracts,
)


def test_sanitize_text():
    text = "\n  This  is  a  \n test    with extraneous  characters!#@*%&   "
    expected_result = "This is a test with extraneous characters!"
    assert sanitize_text(text) == expected_result


def test_extract_arxiv_number():
    class MockTitle:
        def __init__(self):
            self.find_result = [self]

        def find(self, _):
            return self.find_result

        attrs = {"href": "http://arxiv.org/abs/2303.11177"}

    arxiv_number = _extract_arxiv_number(MockTitle())
    assert arxiv_number == "2303.11177"


def test_bulk_download():
    with mock.patch(
        "arxiv_sanity_bot.arxiv_sanity.abstracts.AsyncHTMLSession"
    ) as mock_async_html_session:
        mock_async_html_session_instance = mock_async_html_session.return_value
        mock_async_html_session_instance.run.return_value = [[]]

        result = bulk_download(["http://test.url"])
        assert result == []


def test_get_all_abstracts():
    with mock.patch(
        "arxiv_sanity_bot.arxiv_sanity.abstracts.bulk_download"
    ) as mock_bulk_download:
        mock_bulk_download.return_value = [
            {
                "arxiv": "2303.11177",
                "title": "test abstract",
                "abstract": "test abstract",
                "score": 0,
                "published_on": datetime.now().strftime("%Y-%m-%d"),
            }
        ]

        df = get_all_abstracts(max_pages=1, chunk_size=1)

        assert isinstance(df, pd.DataFrame)
        assert df.shape == (1, 5)
        assert "arxiv" in df.columns
        assert "title" in df.columns
        assert "abstract" in df.columns
        assert "score" in df.columns
        assert "published_on" in df.columns

        expected_df = pd.DataFrame(
            [
                {
                    "arxiv": "2303.11177",
                    "title": "test abstract",
                    "abstract": "test abstract",
                    "score": 0,
                    "published_on": datetime.now().strftime("%Y-%m-%d"),
                }
            ]
        )
        expected_df["published_on"] = pd.to_datetime(expected_df["published_on"])

        pd.testing.assert_frame_equal(df, expected_df)
