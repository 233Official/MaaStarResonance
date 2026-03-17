import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from agent.constant.map_point import MAP_POINT_DATA
from agent.custom.app_manage_action import wait_for_switch
from agent.custom.general.general import ensure_main_page
from agent.custom.general.move_battle import ensure_into_instance, auto_attack, attack_rotate_view, check_alive
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger


@AgentServer.custom_action("UnstableSpacePoint")
class UnstableSpacePointAction(CustomAction):

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        # 先导航过去 TODO 传送点数据未录入
        teleport_or_navigate(context, "阿斯特里斯", "不稳定空间", "导航", MAP_POINT_DATA)
        # 循环检测进入不稳定空间的按钮
        has_entry = ensure_space_entry(context)
        if not has_entry:
            return False

        # 点击进入不稳定空间
        context.tasker.controller.post_click(0, 0).wait()  # TODO 点击进入不稳定空间
        # 选择单双人挑战
        time.sleep(2)
        context.tasker.controller.post_click(0, 0).wait()  # TODO 选择单双人挑战
        # 开始挑战
        time.sleep(2)
        context.tasker.controller.post_click(0, 0).wait()  # TODO 开始挑战

        # 等待加载完成
        time.sleep(2)
        ensure_into_instance(context)

        # 开始自动战斗
        auto_attack(context, 1)

        # 旋转3次视角防止脱仇
        attack_rotate_view(context, 3, 1)

        # 开始检测副本状态和角色存活状态
        while not context.tasker.stopping:
            # 检测是否还在副本内
            img = context.tasker.controller.post_screencap().wait().get()
            is_into_instance = context.run_recognition("图片识别副本退出按钮", img)

            if not is_into_instance:  # 不在副本内
                # 等待场景切换完成
                wait_for_switch(context)
                return True  # 结束任务

            # 检测是否存活并复活
            check_alive(context)

            time.sleep(5)

        logger.error("不稳定空间战斗被手动终止或者出现异常！")
        return False


def ensure_space_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达不稳定空间的入口"""
    start_time = time.time()
    elapsed_time = 0
    # 循环检测是否到达不稳定空间的入口
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img = context.tasker.controller.post_screencap().wait().get()
        is_arrive = context.run_recognition("检测是否到达不稳定空间的入口", img)
        if is_arrive and is_arrive.hit:
            del is_arrive, img
            logger.info(f"检测到已经到达不稳定空间的入口！")
            return True
        del is_arrive, img
        time.sleep(2)
    logger.error("超 120 秒未到达不稳定空间的入口！")
    return False

