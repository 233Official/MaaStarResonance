from maa.context import Context

from agent.logger import logger


def get_login_timeout(context: Context) -> int:
    """获取登录超时时长参数"""
    login_timeout_node = context.get_node_data("获取参数-登录超时时长")
    login_timeout = (login_timeout_node
                     .get("attach", {})
                     .get("login_timeout", 240)
                     ) if login_timeout_node else 240
    logger.info(f"登录超时时长参数: {login_timeout}秒")
    return int(login_timeout)


def get_area_change_timeout(context: Context) -> int:
    """获取场景切换超时时长参数"""
    area_change_timeout_node = context.get_node_data("获取参数-场景切换超时时长")
    area_change_timeout = (area_change_timeout_node
                           .get("attach", {})
                           .get("area_change_timeout", 90)
                           ) if area_change_timeout_node else 90
    logger.info(f"场景切换超时时长参数: {area_change_timeout}秒")
    return int(area_change_timeout)


def get_restart_for_except(context: Context) -> bool:
    """获取是否重启游戏参数"""
    restart_for_except_node = context.get_node_data("获取参数-是否重启游戏")
    restart_for_except = (restart_for_except_node
                          .get("attach", {})
                          .get("restart_for_except", True)
                          ) if restart_for_except_node else True
    logger.info(f"是否重启游戏参数参数: {restart_for_except}")
    return restart_for_except


def get_max_restart_count(context: Context) -> int:
    """获取最大重启游戏次数限制参数"""
    max_restart_count_node = context.get_node_data("获取参数-最大重启游戏次数限制")
    max_restart_count = (max_restart_count_node
                         .get("attach", {})
                         .get("max_restart_count", 5)
                         ) if max_restart_count_node else 5
    logger.info(f"最大重启游戏次数限制参数: {max_restart_count}")
    return int(max_restart_count)


def get_dest_map(context: Context) -> str:
    """获取传送所需地图参数"""
    dest_map_node = context.get_node_data("获取参数-传送所需地图")
    dest_map = (dest_map_node
                         .get("attach", {})
                         .get("dest_map", "")
                         ) if dest_map_node else ""
    logger.info(f"传送所需地图参数: {dest_map}")
    return dest_map


def get_dest_tele_point(context: Context) -> str:
    """获取传送所需传送点参数"""
    dest_tele_point_node = context.get_node_data("获取参数-传送所需传送点")
    dest_tele_point = (dest_tele_point_node
                         .get("attach", {})
                         .get("dest_tele_point", "")
                         ) if dest_tele_point_node else ""
    logger.info(f"传送所需传送点参数: {dest_tele_point}")
    return dest_tele_point

