"""通过 Npcap 插件获取当前角色坐标和朝向的示例。"""

import math
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from agent.logger import logger
from agent.plugin_registry import PluginRegistry


def _get_npcap_plugin():
    """获取已加载的 Npcap 插件实例。

    Returns:
        NpcapPlugin | None: 插件实例，未加载时返回 None
    """
    registry = PluginRegistry.get_instance()
    plugin = registry.get_plugin("maasr_plugin_npcap")
    if plugin is None:
        logger.warning("Npcap 插件未加载，请确认 agent/plugins/ 下存在 maasr_plugin_npcap")
    return plugin


@AgentServer.custom_action("get_player_position")
class GetPlayerPositionAction(CustomAction):
    """获取当前角色坐标和朝向（轮询方式）。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        plugin = _get_npcap_plugin()
        if plugin is None:
            return False

        pos = plugin.get_position()
        if pos is None:
            logger.warning("尚未收到坐标数据，请确认游戏已登录且插件正在抓包")
            return False

        logger.info(
            f"坐标: ({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}), "
            f"朝向: {pos.dir:.4f} rad ({math.degrees(pos.dir):.1f}°)"
        )
        return True


@AgentServer.custom_action("watch_player_position")
class WatchPlayerPositionAction(CustomAction):
    """监听坐标变化（回调方式）。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        plugin = _get_npcap_plugin()
        if plugin is None:
            return False

        def on_position(pos):
            logger.info(
                f"[回调] 坐标: ({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}), "
                f"朝向: {pos.dir:.4f} rad"
            )

        plugin.on_position_update(on_position)
        logger.info("已注册坐标监听回调，持续 30 秒...")
        time.sleep(30)
        plugin.remove_position_callback(on_position)
        logger.info("坐标监听已结束")
        return True


@AgentServer.custom_action("get_player_info")
class GetPlayerInfoAction(CustomAction):
    """获取当前玩家完整信息（名称、职业、等级、HP 等）。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        plugin = _get_npcap_plugin()
        if plugin is None:
            return False

        info = plugin.get_player_info()
        logger.info(f"玩家信息: {info}")
        return True
