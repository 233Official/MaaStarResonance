from maa.context import Context

from agent.attach import attach_param


@attach_param("获取参数-自动钓鱼去的导航位置", "target", "不导航")
def get_fish_navigation(context: Context) -> str:
    """获取钓鱼导航位置参数"""
    ...


@attach_param("获取参数-需要购买的鱼竿配件", "item_name", "普通鱼竿")
def get_fish_rod(context: Context) -> str:
    """获取钓鱼鱼竿配件参数"""
    ...


@attach_param("获取参数-需要购买的鱼饵配件", "item_name", "普通鱼饵")
def get_fish_bait(context: Context) -> str:
    """获取钓鱼鱼饵配件参数"""
    ...


@attach_param("获取参数-是否重启游戏", "restart_for_except", True, bool)
def get_restart_for_except(context: Context) -> bool:
    """获取是否重启游戏参数"""
    ...


@attach_param("获取参数-最大重启游戏次数限制", "max_restart_count", 5, int)
def get_max_restart_count(context: Context) -> int:
    """获取最大重启游戏次数限制参数"""
    ...


def get_fish_equipment(context: Context, type_str: str) -> str:
    """获取钓鱼配件参数（动态节点名，无法用装饰器）"""
    from agent.logger import logger

    node = context.get_node_data(f"获取参数-需要购买的{type_str}配件")
    value = (node.get("attach", {}).get("item_name", f"普通{type_str}")) if node else f"普通{type_str}"
    logger.info("需要购买的{}: {}", type_str, value)
    return str(value)
