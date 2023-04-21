import pytest
from unittest import mock
from datetime import datetime
from arxiv_sanity_bot.events import (
    _Event,
    FatalErrorEvent,
    InfoEvent,
    RetryableErrorEvent,
)


def test_event_repr():
    class TestEvent(_Event):
        def handle(self):
            pass

    with mock.patch("inspect.currentframe") as mock_currentframe:
        frame = mock.MagicMock()
        frame.f_back.f_back.f_back.f_back.f_back = frame
        frame.f_code.co_filename = "test.py"
        frame.f_lineno = 42
        mock_currentframe.return_value = frame

        test_event = TestEvent(msg="test message", context={"key": "value"})

        event_info = test_event._to_dict()
        expected_info = {
            "event": "TestEvent",
            "msg": "test message",
            "context": {"key": "value"},
            "caller": "test.py:42",
        }
        assert event_info == expected_info


def test_fatal_error_event():
    with mock.patch(
        "arxiv_sanity_bot.events.logger.error"
    ) as mock_logger_error, mock.patch("sys.exit") as mock_sys_exit:
        FatalErrorEvent(msg="fatal error", context={"error": "test"})

        mock_logger_error.assert_called_once()
        mock_sys_exit.assert_called_once_with(-1)


def test_info_event():
    with mock.patch("arxiv_sanity_bot.events.logger.info") as mock_logger_info:
        InfoEvent(msg="info message", context={"info": "test"})

        mock_logger_info.assert_called_once()


def test_retryable_error_event():
    with mock.patch("arxiv_sanity_bot.events.logger.error") as mock_logger_error:
        RetryableErrorEvent(msg="retryable error", context={"error": "test"})

        mock_logger_error.assert_called_once()
