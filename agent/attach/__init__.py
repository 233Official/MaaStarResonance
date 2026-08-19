from typing import Any, Callable, TypeVar

from maa.context import Context

from agent.logger import logger

T = TypeVar("T")


def attach_param(
    node_name: str,
    key: str,
    default: T,
    type_cast: Callable[[Any], T] = str,
    log_msg: str | None = None,
) -> Callable[[Callable[..., T]], Callable[[Context], T]]:
    """装饰器：从 pipeline attach 节点读取参数。

    消除每个 attach 函数中重复的 get_node_data → get attach → get key → 类型转换 → 打日志 模板代码。

    Args:
        node_name: pipeline 节点名称（如 "获取参数-登录超时时长"）
        key: attach 字典中的键名（如 "login_timeout"）
        default: 节点或键不存在时的默认值
        type_cast: 类型转换函数（str / int / bool / list[str] 等）
        log_msg: 自定义日志消息，为 None 时自动生成

    Returns:
        装饰器函数，被装饰的函数只需写 docstring，无需实现体

    Example:
        @attach_param("获取参数-登录超时时长", "login_timeout", 300, int)
        def get_login_timeout(context: Context) -> int:
            \"\"\"获取登录超时时长参数\"\"\"
    """

    def decorator(func: Callable[..., T]) -> Callable[[Context], T]:
        def wrapper(context: Context) -> T:
            node = context.get_node_data(node_name)
            value = (node.get("attach", {}).get(key, default)) if node else default
            result = type_cast(value)
            msg = log_msg or (func.__doc__ or node_name).strip()
            logger.info("{}: {}", msg, result)
            return result

        # 保留原函数的元信息
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        return wrapper

    return decorator


def attach_param_list(
    node_name: str,
    key: str,
    separator: str = ",",
    log_msg: str | None = None,
) -> Callable[[Callable[..., list[str]]], Callable[[Context], list[str]]]:
    """装饰器：从 pipeline attach 节点读取逗号分隔的列表参数。

    适用于 "1,201,302" 这类逗号分隔的 ID 列表参数。

    Args:
        node_name: pipeline 节点名称
        key: attach 字典中的键名
        separator: 分隔符，默认逗号
        log_msg: 自定义日志消息，为 None 时自动生成

    Example:
        @attach_param_list("获取参数-需要切换的世界分线ID列表", "line_ids")
        def get_world_line_id_list(context: Context) -> list[str]:
            \"\"\"获取需要切换的世界分线ID列表参数\"\"\"
    """

    def decorator(func: Callable[..., list[str]]) -> Callable[[Context], list[str]]:
        def wrapper(context: Context) -> list[str]:
            node = context.get_node_data(node_name)
            value = (node.get("attach", {}).get(key, "")) if node else ""
            result = str(value).split(separator) if value else []
            msg = log_msg or (func.__doc__ or node_name).strip()
            logger.info("{}: {}", msg, result)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        return wrapper

    return decorator


__all__ = ["attach_param", "attach_param_list"]
