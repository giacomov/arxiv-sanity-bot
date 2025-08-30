from unittest.mock import patch, Mock

import pytest

from arxiv_sanity_bot.models.chatGPT import ChatGPT


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
        
        chatgpt = ChatGPT()
        summary = chatgpt.summarize_abstract(abstract)
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
        
        chatgpt = ChatGPT()
        with pytest.raises(SystemExit):
            chatgpt.summarize_abstract(abstract)
