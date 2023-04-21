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

    assert isinstance(logger.logger.handlers[0], logging.FileHandler)
