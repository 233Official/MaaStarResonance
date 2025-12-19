"""项目级日志配置。"""

from __future__ import annotations

import sys

from loguru import logger as _logger


def sink_function(message):
    """根据日志级别生成前缀并拼接消息"""
    record = message.record
    level_name = record["level"].name
    prefix = level_name.lower() + ":"
    text = f"{prefix} [{record['time'].strftime('%Y-%m-%d %H:%M:%S')}] {record['message']}\n"
    # 输出到 stdout
    sys.stdout.write(text)


# 重新配置默认输出，确保格式统一且线程安全。
_logger.remove()
_logger.add(
    sink_function,
    # level="INFO",
    level="DEBUG",
    enqueue=True,
    backtrace=True,
    diagnose=False,
)

logger = _logger

__all__ = ["logger"]
