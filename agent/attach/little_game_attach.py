from maa.context import Context

from agent.attach import attach_param


@attach_param("获取参数-第一次小游戏前所需切换的分线", "need_line", 0, int)
def get_game_need_line(context: Context) -> int:
    """获取小游戏需要切换的分线"""
    ...


@attach_param("获取参数-游戏等待超时时间", "wait_time_limit", 0, int)
def get_game_wait_time_limit(context: Context) -> int:
    """获取游戏等待超时时间"""
    ...


@attach_param("获取参数-躲猫猫队伍类型", "hide_team_type", "无")
def get_hide_team_type(context: Context) -> str:
    """获取躲猫猫队伍类型：无 / 单人匹配游戏 / 组队匹配游戏（队长） / 组队匹配游戏（队员） / 组队私人游戏（队长，队伍人数须>=5） / 组队私人游戏（队员）"""
    ...


@attach_param("获取参数-麻将队伍类型", "maj_team_type", "无")
def get_maj_team_type(context: Context) -> str:
    """获取麻将队伍类型：无 / 单人匹配游戏 / 组队私人游戏（队长） / 组队私人游戏（队员）"""
    ...


@attach_param("获取参数-载具赛队伍类型", "vehicle_team_type", "无")
def get_vehicle_team_type(context: Context) -> str:
    """获取载具赛队伍类型：无 / 单人匹配游戏 / 组队匹配游戏（队长） / 组队匹配游戏（队员）"""
    ...
