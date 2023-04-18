import abc
import dataclasses
import inspect
import sys
from datetime import datetime
from typing import Dict, Any

import yaml

from arxiv_sanity_bot.logger import logger


@dataclasses.dataclass
class _Event:

    msg: str
    context: Dict[Any, Any] = None

    def __post_init__(self):
        self.handle()

    def _to_dict(self):
        d = dataclasses.asdict(self)
        d["event"] = type(self).__name__

        # Add module and line number of the caller
        frame = inspect.currentframe()
        calling_frame = frame.f_back.f_back.f_back.f_back.f_back
        d["caller"] = f"{calling_frame.f_code.co_filename}:{calling_frame.f_lineno}"

        # Avoid printing a null context
        if d.get("context") is None:
            d.pop("context")

        return d

    def __repr__(self):

        return yaml.safe_dump({datetime.now(): self._to_dict()}, indent=4)

    @abc.abstractmethod
    def handle(self):
        ...


@dataclasses.dataclass(repr=False)
class FatalErrorEvent(_Event):

    def handle(self):
        # TODO: send an email
        logger.error(str(self))
        sys.exit(-1)


@dataclasses.dataclass(repr=False)
class InfoEvent(_Event):

    def handle(self):
        logger.info(str(self))


@dataclasses.dataclass(repr=False)
class RetryableErrorEvent(_Event):

    def handle(self):
        logger.error(str(self))
