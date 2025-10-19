"""项目级日志配置。"""

from __future__ import annotations

import sys
from typing import Final

from loguru import logger as _logger

_DEFAULT_FORMAT: Final[str] = "[{time:YYYY-MM-DD HH:mm:ss}] <{level}> {message}"

# 重新配置默认输出，确保格式统一且线程安全。
_logger.remove()
_logger.add(
    sys.stdout,
    format=_DEFAULT_FORMAT,
    # level="INFO",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=False,
)

logger = _logger

__all__ = ["logger"]
