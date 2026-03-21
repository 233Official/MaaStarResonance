import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.constant.map_point import NAVIGATE_DATA
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
        # 先导航过去
        teleport_or_navigate(context, "阿斯特里斯", "不稳定空间", "导航", NAVIGATE_DATA)
        # 循环检测进入不稳定空间的按钮
        has_entry = ensure_space_entry(context)
        if not has_entry:
            return False

        # 点击进入不稳定空间
        context.tasker.controller.post_click(916, 345).wait()
        # 选择单双人挑战
        time.sleep(2)
        context.tasker.controller.post_click(915, 591).wait()
        # 开始挑战
        time.sleep(2)
        context.tasker.controller.post_click(1170, 657).wait()

        # 等待加载完成
        time.sleep(2)
        ensure_into_instance(context)

        # 开始自动战斗
        logger.info("打开自动战斗...")
        auto_attack(context, 1)

        # 旋转3次视角防止脱仇
        logger.info("旋转3次视角防止脱仇然后继续战斗...")
        attack_rotate_view(context, 3, 1)

        # 开始检测副本状态和角色存活状态
        while not context.tasker.stopping:
            # 检测是否还在副本内
            img = context.tasker.controller.post_screencap().wait().get()
            is_into_instance = context.run_recognition("图片识别副本退出按钮", img)

            if is_into_instance and not is_into_instance.hit:  # 不在副本内
                # 等待场景切换完成
                logger.info("战斗完成，等待返回主界面...")
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
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "不稳定",
                    "roi": [875, 330, 61, 30],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            del ocr_result, img
            logger.info(f"检测到已经到达不稳定空间的入口！")
            return True
        del ocr_result, img
        time.sleep(2)
    logger.error("超 120 秒未到达不稳定空间的入口！")
    return False

