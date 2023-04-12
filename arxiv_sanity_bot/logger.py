import logging
import os
import warnings


def _get_logging_level(default: str = "DEBUG"):

    lv = os.environ.get("LOG_LEVEL", default)

    try:
        lv = getattr(logging, lv)
    except AttributeError:
        warnings.warn(f"LOG_LEVEL has an invalid value of {lv}. Defaulting to {default}")
        return getattr(logging, default)
    else:
        return lv


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
)

logger = logging.getLogger("arxiv-sanity-bot")
logger.setLevel(_get_logging_level())
logger.handlers = [
        logging.FileHandler('arxiv-sanity-bot.log')
    ]
