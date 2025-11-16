# 省电模式相关逻辑
# agent/power_mode.py
from __future__ import annotations
from functools import wraps
from typing import Callable, TypeVar, Protocol, Any
from maa.context import Context
from maa.custom_action import CustomAction
from logger import logger


class ExitPowerSaveFunc(Protocol):
    def __call__(self, context: Context) -> Any: ...


def default_exit_power_save(context: Context) -> None:
    """默认的退出省电模式逻辑

    Args:
        context (Context): 当前上下文
    """
    try:
        # 示例：
        img = context.tasker.controller.post_screencap().wait().get()
        detail = context.run_recognition("识别是否在省电模式", img)
        if detail and detail.hit:
            context.run_task(entry="从省电模式唤醒")
        logger.debug("[ExitPowerSave] 尝试退出省电模式")
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[ExitPowerSave] 退出省电模式异常: {exc}")


def exit_power_saving_mode(
    exit_func: ExitPowerSaveFunc | None = None,
    force: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    方法装饰器：在 run 执行前退出省电模式。
    Args:
        exit_func: 自定义退出逻辑，默认为 default_exit_power_save
    """
    real_exit = exit_func or default_exit_power_save

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: CustomAction, context: Context, *args, **kwargs):
            try:
                real_exit(context)
                logger.debug("[ExitPowerSave] 成功退出省电模式")
            except Exception as exc:  # pragma: no cover
                logger.error(f"[ExitPowerSave] 退出省电模式失败: {exc}")
            return fn(self, context, *args, **kwargs)

        return wrapper

    return decorator
