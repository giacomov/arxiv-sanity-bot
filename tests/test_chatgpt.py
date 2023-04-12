from unittest.mock import patch

import pytest

from arxiv_sanity_bot.models.chatGPT import ChatGPT

# Sample response from OpenAI API
sample_response = {
    "choices": [
        {
            "message": {
                "content": "This is a sample summary."
            }
        }
    ]
}


def test_summarize_abstract():
    chatgpt = ChatGPT()
    abstract = "This is a sample abstract."
    expected_summary = "This is a sample summary."

    with patch('openai.ChatCompletion.create', return_value=sample_response):
        # Test if the summary is generated as expected
        summary = chatgpt.summarize_abstract(abstract)
        assert summary == expected_summary

    # Test the case where the model produces a long summary
    long_summary_response = {
        "choices": [
            {
                "message": {
                    "content": "This is a sample summary that is too long for a tweet." * 10
                }
            }
        ]
    }

    with patch('openai.ChatCompletion.create', return_value=long_summary_response):

        with pytest.raises(SystemExit):
            _ = chatgpt.summarize_abstract(abstract)
