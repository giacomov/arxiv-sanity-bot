import logging
import os
import pytest
from unittest.mock import patch


def test_get_logging_level():
    from arxiv_sanity_bot import logger

    with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
        logging_level = logger._get_logging_level()
        assert logging_level == logging.INFO

    with patch.dict(os.environ, {"LOG_LEVEL": "NON_EXISTENT"}):
        with pytest.warns(UserWarning, match="LOG_LEVEL has an invalid value"):
            logging_level = logger._get_logging_level()
            assert logging_level == logging.DEBUG


def test_logging_configuration():
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        from arxiv_sanity_bot import logger

        assert logger.logger.level == logger._get_logging_level()

    # Check that we have both console and file handlers
    root_logger = logging.getLogger("arxiv_sanity_bot")
    assert len(root_logger.handlers) >= 2
    handler_types = [type(h) for h in root_logger.handlers]
    assert logging.StreamHandler in handler_types
    assert logging.FileHandler in handler_types
