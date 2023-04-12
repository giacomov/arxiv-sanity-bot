import pytest
import httpx
from unittest.mock import AsyncMock, patch
from arxiv_sanity_bot.altmetric.scores import _gather_one_score, gather_scores

# Sample API response
sample_response = {
    "published_on": 1623135600,
    "history": {
        "at": 123,
    },
}


@pytest.mark.asyncio
async def test_gather_one_score():
    async def mock_response(url: str):
        response = httpx.Response(status_code=200, json=sample_response)
        return response

    with patch(
        "httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_response
    ):
        arxiv_id = "2106.12345"
        result = await _gather_one_score(arxiv_id)

    expected_result = {
        "score": sample_response["history"]["at"],
        "published_on": "2021-06-08T00:00:00-07:00",
    }

    assert result == expected_result

    # Test a non-200 status code response
    async def mock_response_with_error(url: str):
        response = httpx.Response(status_code=404)
        return response

    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=mock_response_with_error,
    ):
        result = await _gather_one_score(arxiv_id)

    expected_result = {
        "score": -1,
        "published_on": None,
    }

    assert result == expected_result


@pytest.mark.asyncio
async def test_gather_scores():
    arxiv_ids = ["2106.12345", "2106.23456", "2106.34567"]
    chunk_size = 2

    with patch(
        "arxiv_sanity_bot.altmetric.scores._gather_one_score",
        return_value={"score": 123, "published_on": "2021-06-08T00:00:00"},
    ):
        results = await gather_scores(arxiv_ids, chunk_size=chunk_size)

    assert len(results) == len(arxiv_ids)
    for result in results:
        assert result == {"score": 123, "published_on": "2021-06-08T00:00:00"}
