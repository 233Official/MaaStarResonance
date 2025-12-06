"""项目级日志配置。"""

from __future__ import annotations

import sys

from loguru import logger as _logger


def format_record(record):
    """根据日志级别生成前缀并拼接消息."""
    level_name = record["level"].name
    prefix = level_name.lower() + ":"
    return f"{prefix} [{record['time'].strftime('%Y-%m-%d %H:%M:%S')}] {record['message']}\n"


# 重新配置默认输出，确保格式统一且线程安全。
_logger.remove()
_logger.add(
    sys.stdout,
    format=format_record,
    # level="INFO",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=False,
)

logger = _logger

__all__ = ["logger"]
