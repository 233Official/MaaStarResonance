import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction, RecognitionDetail

from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.app_manage_action import wait_for_switch
from agent.custom.general.general import ensure_main_page
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.general.world_line_switcher import switch_line
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


@AgentServer.custom_action("BeatChenMinPoint")
class BeatChenMinPointAction(CustomAction):

    def __init__(self):
        super().__init__()
        self.beat_count = None

    @exit_power_saving_mode()
    @ensure_main_page()
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取参数
        self.beat_count = 0
        params = CustomActionParam(argv.custom_action_param)
        max_beat_count = int(params.data["max_beat_count"]) if params.data["max_beat_count"] else 0
        logger.info(f"本次任务设置的最大暴打次数: {max_beat_count if max_beat_count != 0 else '无限'}")

        while not context.tasker.stopping:
            # 检查是否已经钓到足够数量的鱼鱼了
            if max_beat_count != 0 and max_beat_count <= self.beat_count:
                logger.info(f"已成功暴打了您所配置的{self.beat_count}次陈敏，暴打结束！")
                return True

            # 先导航过去
            teleport_or_navigate(context, "游星岛", "异次元惩戒", "导航", NAVIGATE_DATA)

            # 循环检测进入暴打陈敏的按钮
            has_entry = ensure_chen_entry(context)
            if not has_entry:
                return False

            # 循环检测是否可进去暴打，不能就切线
            ensure_can_beat_chen(context)

            # 向前走几步
            context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_W"])
            time.sleep(0.8)
            context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_W"])

            # 等待20秒
            time.sleep(20)

            # 按几下攻击键
            context.tasker.controller.post_click(1122, 550, 1, 1)
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1)
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1)
            time.sleep(5)

            # 等待暴打结束
            wait_for_end(context)

            # 等待5秒后开启下一轮暴打
            time.sleep(5)

        logger.warning("暴打陈敏已结束！")
        return True


def ensure_chen_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达暴打陈敏的入口"""
    start_time = time.time()
    elapsed_time = 0
    # 循环检测是否到达暴打陈敏的入口
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "报名",
                    "roi": [871, 329, 51, 30],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            del ocr_result, img
            logger.info(f"检测到已经到达暴打陈敏的入口！")
            return True
        del ocr_result, img
        time.sleep(2)
    logger.error("超 120 秒未到达暴打陈敏的入口！")
    return False


def ensure_can_beat_chen(context: Context) -> bool:
    """
    循环检测是否可进入暴打陈敏，不可进入则切线
    """
    line_list = ["30", "31", "32", "33", "34", "35", "36", "37", "38", "39","40", "41", "42", "43", "44", "45", "46", "47", "48", "49"]

    for line in line_list:
        if context.tasker.stopping:
            logger.warning("暴打陈敏检测已被手动停止")
            return False

        # 点击进入暴打陈敏
        context.tasker.controller.post_click(895, 344).wait()
        time.sleep(0.5)

        # 检测是否已经进入暴打陈敏
        if check_can_beat_chen(context):
            logger.info("检测到当前线路可以进入暴打陈敏！")
            return True

        # 切线
        logger.info("当前线路不可进入暴打陈敏，准备切线...")
        switch_line(context, [line])
        time.sleep(1)

        # 等待场景切换完成
        wait_for_switch(context)

    logger.error(f"分线30至49线均无法进入暴打陈敏！")
    return False


def check_can_beat_chen(context: Context) -> bool:
    """
    检测当前是否可进入暴打陈敏
    """
    img = context.tasker.controller.post_screencap().wait().get()
    try:
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "当前活动无法报名，请稍后在等待阶段报名。",
                    "roi": [457, 181, 352, 32],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            logger.info("当前分线已有玩家正在暴打陈敏，将尝试自动切线")
            return False

        logger.info("已成功进入暴打陈敏小游戏")
        return True
    finally:
        del img


def wait_for_end(context: Context, timeout: int = 120) -> bool:
    """等待暴打陈敏结束"""
    start_time = time.time()
    elapsed_time = 0
    # 循环检测暴打陈敏结束
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "异次元惩戒",
                    "roi": [77, 214, 92, 27],
                }
            },
        )
        if ocr_result and ocr_result.hit:
            del ocr_result, img
            logger.info(f"检测到暴打陈敏结束！")
            return True
        del ocr_result, img
        time.sleep(5)
    logger.error("超 120 秒未检测到暴打陈敏结束！")
    return False
