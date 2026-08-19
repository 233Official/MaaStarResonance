from maa.context import Context

from agent.attach import attach_param, attach_param_list


@attach_param("获取参数-登录超时时长", "login_timeout", 300, int)
def get_login_timeout(context: Context) -> int:
    """获取登录超时时长参数"""
    ...


@attach_param("获取参数-场景切换超时时长", "area_change_timeout", 90, int)
def get_area_change_timeout(context: Context) -> int:
    """获取场景切换超时时长参数"""
    ...


@attach_param("获取参数-传送所需地图", "dest_map", "")
def get_dest_tele_map(context: Context) -> str:
    """获取传送所需地图参数"""
    ...


@attach_param("获取参数-传送所需传送点", "dest_tele_point", "")
def get_dest_tele_point(context: Context) -> str:
    """获取传送所需传送点参数"""
    ...


@attach_param("获取参数-导航所需地图", "dest_map", "")
def get_dest_navi_map(context: Context) -> str:
    """获取导航所需地图参数"""
    ...


@attach_param("获取参数-导航所需导航点", "dest_navigate_point", "")
def get_dest_navigate_point(context: Context) -> str:
    """获取导航所需导航点参数"""
    ...


@attach_param_list("获取参数-需要切换的世界分线ID列表", "line_ids")
def get_world_line_id_list(context: Context) -> list[str]:
    """获取需要切换的世界分线ID列表参数"""
    ...


@attach_param("获取参数-需要刷的茧", "cocoon_name", "")
def get_need_cocoon_name(context: Context) -> str:
    """获取需要刷的茧参数"""
    ...
