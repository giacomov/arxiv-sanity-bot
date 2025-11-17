import pytest
from unittest.mock import patch
from datetime import datetime

from arxiv_sanity_bot.schemas import RawPaper, RankedPaper, PaperSource
from arxiv_sanity_bot.ranking.ranked_papers import (
    _extract_field,
    _from_alphaxiv,
    _from_huggingface,
    fetch_alphaxiv_papers,
    fetch_hf_papers_date_range,
    get_all_abstracts,
    get_url,
    _merge_and_score_papers,
    _parse_publication_date,
    _filter_by_date_range,
)


@pytest.fixture
def raw_paper():
    def _make(arxiv_id="2411.12345", title="Test", abstract="Test abstract",
              published_on="2025-11-10T00:00:00.000Z", votes=None):
        return RawPaper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            published_on=published_on,
            votes=votes,
        )
    return _make


@pytest.fixture
def scored_paper():
    def _make(arxiv_id="2411.12345", score=1, alphaxiv_rank=None, hf_rank=None,
              source=PaperSource.ALPHAXIV, **kwargs):
        return RankedPaper(
            arxiv_id=arxiv_id,
            title=kwargs.get("title", "Test"),
            abstract=kwargs.get("abstract", "Test abstract"),
            published_on=kwargs.get("published_on", "2025-11-10T00:00:00.000Z"),
            score=score,
            alphaxiv_rank=alphaxiv_rank,
            hf_rank=hf_rank,
            source=source,
        )
    return _make


@pytest.fixture
def date_range():
    return datetime(2025, 11, 9), datetime(2025, 11, 15)


def test_extract_field_top_level():
    assert _extract_field({"universal_paper_id": "2411.12345"}, ["universal_paper_id"]) == "2411.12345"


def test_extract_field_nested():
    assert _extract_field({"paper": {"id": "2411.67890"}}, ["id"], nested_keys=["paper"]) == "2411.67890"


def test_extract_field_fallback():
    assert _extract_field({"id": "2411.11111"}, ["universal_paper_id", "id"]) == "2411.11111"


def test_extract_field_not_found():
    assert _extract_field({"other_field": "value"}, ["id"]) is None


def test_raw_paper_from_alphaxiv():
    data = {
        "universal_paper_id": "2411.12345",
        "title": "Test Paper",
        "abstract": "Test abstract",
        "publication_date": "2025-11-13T00:00:00.000Z",
    }
    paper = _from_alphaxiv(data)

    assert paper.arxiv_id == "2411.12345"
    assert paper.title == "Test Paper"


def test_raw_paper_from_huggingface():
    data = {
        "paper": {"id": "2411.67890", "title": "HF Paper", "summary": "HF abstract"},
        "publishedAt": "2025-11-10T00:00:00.000Z",
    }
    paper = _from_huggingface(data)

    assert paper.arxiv_id == "2411.67890"
    assert paper.title == "HF Paper"


@pytest.mark.parametrize("alphaxiv_rank,hf_rank,expected", [
    (5, 3, 4.0),
    (5, None, 5.0),
    (None, 3, 3.0),
    (None, None, float("inf")),
])
def test_scored_paper_average_rank(scored_paper, alphaxiv_rank, hf_rank, expected):
    paper = scored_paper(alphaxiv_rank=alphaxiv_rank, hf_rank=hf_rank)
    assert paper.average_rank == expected


@patch("arxiv_sanity_bot.ranking.ranked_papers._fetch_alphaxiv_page")
def test_fetch_alphaxiv_papers(mock_fetch_page, raw_paper):
    mock_fetch_page.side_effect = [
        [
            raw_paper(arxiv_id="2411.12345", title="Paper 1", votes=10),
            raw_paper(arxiv_id="2411.12346", title="Paper 2", votes=5),
            raw_paper(arxiv_id="2411.12347", title="Paper 3", votes=1),
        ],
        []
    ]

    papers = fetch_alphaxiv_papers(days=7, max_papers=100, top_percentile=66.6)

    assert len(papers) == 1
    assert papers[0].arxiv_id == "2411.12345"


@patch("arxiv_sanity_bot.ranking.ranked_papers._fetch_hf_papers_for_date")
@patch("arxiv_sanity_bot.ranking.ranked_papers.time.sleep")
def test_fetch_hf_papers_date_range(mock_sleep, mock_fetch, raw_paper):
    mock_fetch.return_value = [raw_paper(arxiv_id="2411.67890")]

    papers = fetch_hf_papers_date_range(days=2)

    assert mock_fetch.call_count == 2
    assert len(papers) == 2


def test_merge_and_score_papers(raw_paper):
    alphaxiv_papers = [
        raw_paper(arxiv_id="2411.11111", title="Paper in both"),
        raw_paper(arxiv_id="2411.22222", title="Paper only in alphaXiv"),
    ]
    hf_papers = [
        raw_paper(arxiv_id="2411.11111", title="Paper in both"),
        raw_paper(arxiv_id="2411.33333", title="Paper only in HF"),
    ]

    scored_papers = _merge_and_score_papers(alphaxiv_papers, hf_papers)

    assert len(scored_papers) == 3
    assert scored_papers[0].arxiv_id == "2411.11111"
    assert scored_papers[0].score == 2
    assert scored_papers[0].source == PaperSource.BOTH


def test_parse_publication_date_valid():
    parsed = _parse_publication_date("2025-11-13T18:59:53.000Z")
    assert parsed.year == 2025
    assert parsed.month == 11
    assert parsed.day == 13


def test_parse_publication_date_invalid():
    assert _parse_publication_date("invalid") is None


def test_filter_by_date_range(scored_paper, date_range):
    after, before = date_range
    papers = [
        scored_paper(arxiv_id="2411.11111", published_on="2025-11-10T00:00:00.000Z"),
        scored_paper(arxiv_id="2411.22222", published_on="2025-11-08T00:00:00.000Z"),
    ]

    filtered = _filter_by_date_range(papers, after, before)

    assert len(filtered) == 1
    assert filtered[0].arxiv_id == "2411.11111"


@patch("arxiv_sanity_bot.ranking.ranked_papers.fetch_alphaxiv_papers")
@patch("arxiv_sanity_bot.ranking.ranked_papers.fetch_hf_papers_date_range")
def test_get_all_abstracts_scoring(mock_fetch_hf, mock_fetch_alphaxiv, raw_paper, date_range):
    mock_fetch_alphaxiv.return_value = [
        raw_paper(arxiv_id="2411.11111", title="Paper in both"),
        raw_paper(arxiv_id="2411.22222", title="Paper only in alphaXiv"),
    ]
    mock_fetch_hf.return_value = [
        raw_paper(arxiv_id="2411.11111", title="Paper in both"),
        raw_paper(arxiv_id="2411.33333", title="Paper only in HF"),
    ]

    after, before = date_range
    df = get_all_abstracts(after, before)

    assert len(df) == 3
    assert df[df["arxiv"] == "2411.11111"].iloc[0]["score"] == 2
    assert df[df["arxiv"] == "2411.22222"].iloc[0]["score"] == 1
    assert df[df["arxiv"] == "2411.33333"].iloc[0]["score"] == 1


@patch("arxiv_sanity_bot.ranking.ranked_papers.fetch_alphaxiv_papers")
@patch("arxiv_sanity_bot.ranking.ranked_papers.fetch_hf_papers_date_range")
def test_get_all_abstracts_sorting(mock_fetch_hf, mock_fetch_alphaxiv, raw_paper, date_range):
    mock_fetch_alphaxiv.return_value = [
        raw_paper(arxiv_id="2411.aaaaa", title="Paper A"),
        raw_paper(arxiv_id="2411.bbbbb", title="Paper B"),
        raw_paper(arxiv_id="2411.ccccc", title="Paper C"),
    ]
    mock_fetch_hf.return_value = [
        raw_paper(arxiv_id="2411.aaaaa", title="Paper A"),
        raw_paper(arxiv_id="2411.bbbbb", title="Paper B"),
    ]

    after, before = date_range
    df = get_all_abstracts(after, before)

    assert len(df) == 3
    assert df.iloc[0]["arxiv"] == "2411.aaaaa"
    assert df.iloc[0]["score"] == 2
    assert df.iloc[1]["arxiv"] == "2411.bbbbb"
    assert df.iloc[1]["score"] == 2
    assert df.iloc[2]["arxiv"] == "2411.ccccc"
    assert df.iloc[2]["score"] == 1


def test_get_url():
    assert get_url("2411.12345") == "https://arxiv.org/abs/2411.12345"
