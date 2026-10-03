from unittest.mock import patch, Mock

import httpx
import openai
import pytest

from arxiv_sanity_bot.models.openai import OpenAI
from arxiv_sanity_bot.logger import FatalError


def _api_error(error_cls, status_code, body):
    response = httpx.Response(
        status_code, request=httpx.Request("POST", "https://api.openai.com/v1/x")
    )
    return error_cls(body.get("message", "error"), response=response, body=body)


def _mock_completion(content):
    completion = Mock()
    completion.choices = [Mock()]
    completion.choices[0].message.content = content
    return completion


def test_summarize_abstract():
    abstract = "This is a sample abstract."
    expected_summary = "This is a sample summary."

    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = expected_summary

    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        openai_model = OpenAI()
        summary = openai_model.summarize_abstract(abstract)
        assert summary == expected_summary

    # Test long summary case
    long_summary = "This is a sample summary that is too long for a tweet." * 10
    mock_long_completion = Mock()
    mock_long_completion.choices = [Mock()]
    mock_long_completion.choices[0].message.content = long_summary

    with patch("openai.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_long_completion
        mock_openai.return_value = mock_client

        openai_model = OpenAI()
        with pytest.raises(FatalError):
            openai_model.summarize_abstract(abstract)


def test_exhausted_credits_fail_fast():
    quota_error = _api_error(
        openai.RateLimitError,
        429,
        {
            "message": "You have no credits remaining.",
            "type": "insufficient_quota",
            "param": None,
            "code": "credit_balance_exhausted",
        },
    )

    with (
        patch("openai.OpenAI") as mock_openai,
        patch("arxiv_sanity_bot.models.openai.time.sleep") as mock_sleep,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = quota_error
        mock_openai.return_value = mock_client

        with pytest.raises(FatalError, match="no credits remaining"):
            OpenAI().summarize_abstract("An abstract.")

    assert mock_client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()


def test_invalid_api_key_fails_fast():
    auth_error = _api_error(
        openai.AuthenticationError,
        401,
        {"message": "Incorrect API key provided", "type": "invalid_request_error"},
    )

    with (
        patch("openai.OpenAI") as mock_openai,
        patch("arxiv_sanity_bot.models.openai.time.sleep") as mock_sleep,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = auth_error
        mock_openai.return_value = mock_client

        with pytest.raises(FatalError):
            OpenAI().generate_bot_summary(10, 3)

    assert mock_client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()


def test_transient_rate_limit_is_retried():
    transient_error = _api_error(
        openai.RateLimitError,
        429,
        {
            "message": "Rate limit reached for requests",
            "type": "requests",
            "code": "rate_limit_exceeded",
        },
    )

    with (
        patch("openai.OpenAI") as mock_openai,
        patch("arxiv_sanity_bot.models.openai.time.sleep") as mock_sleep,
    ):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            transient_error,
            _mock_completion("A short summary."),
        ]
        mock_openai.return_value = mock_client

        assert OpenAI().summarize_abstract("An abstract.") == "A short summary."

    assert mock_client.chat.completions.create.call_count == 2
    assert mock_sleep.call_count == 1
