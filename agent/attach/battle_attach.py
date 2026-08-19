from maa.context import Context

from agent.attach import attach_param


@attach_param("获取参数-不稳定空间队伍类型", "unstable_space_type", "无")
def get_unstable_space_type(context: Context) -> str:
    """获取不稳定空间队伍类型：无 / 单人匹配游戏 / 组队匹配游戏（队长） / 组队匹配游戏（队员）"""
    ...


@attach_param("获取参数-是否开启自动战斗", "use_auto_attack", True, bool)
def get_use_auto_attack(context: Context) -> bool:
    """获取战斗是否开启自动战斗"""
    ...
