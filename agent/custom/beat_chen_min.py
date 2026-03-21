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
            # 检查是否已经暴打足够次数了
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
            logger.info("向前走几步靠近陈敏，等待10秒后开始暴打3次")
            context.tasker.controller.post_key_down(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()
            time.sleep(0.8)
            context.tasker.controller.post_key_up(ANDROID_KEY_EVENT_DATA["KEYCODE_W"]).wait()

            # 等待10秒
            time.sleep(10)

            # 按几下攻击键
            context.tasker.controller.post_click(1122, 550, 1, 1).wait()
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1).wait()
            time.sleep(5)
            context.tasker.controller.post_click(1122, 550, 1, 1).wait()
            time.sleep(5)

            # 等待55秒后开启下一轮暴打
            logger.info("等待55秒暴打结束...")
            wait_count = 0
            while wait_count < 11 and not context.tasker.stopping:
                wait_count += 1
                time.sleep(5)
            
            self.beat_count += 1

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
    循环检测是否可进入暴打陈敏，不可进入则切线。
    30~49 线全部尝试一轮，若都失败则返回 False。
    """
    line_list = [
        "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
        "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "50", "51", "52", "53", "54", "55", "56", "57", "58", "59"
    ]

    tried_count = 0
    total_lines = len(line_list)

    while tried_count < total_lines:
        if context.tasker.stopping:
            logger.warning("暴打陈敏检测已被手动停止")
            return False

        # 获取当前索引 和 尝试的分线
        index = tried_count % total_lines
        current_line = line_list[index]
        logger.info(f"准备在 {current_line} 分线尝试暴打陈敏")

        # 先点击进入按钮，并等待 6 秒看是否进入小游戏
        context.tasker.controller.post_click(895, 344).wait()
        time.sleep(6)

        # 检测是否已经进入暴打陈敏游戏
        if check_can_beat_chen(context):
            logger.info(f"检测到当前线路 {current_line} 已经进入暴打陈敏游戏")
            return True
        else:
            logger.info(f"当前线路 {current_line} 不可进入暴打陈敏，准备切线...")

        # 当前的分线列表
        need_switch_list = line_list[index:] + line_list[:index]
        # 尝试切换分线
        has_next = switch_line(context, need_switch_list)
        # 切换失败，通常表示已经在这条线了
        if not has_next:
            break

        # 等待场景切换完成
        wait_for_switch(context)
        # 尝试次数 + 1
        tried_count += 1

    logger.error("分线 30 至 49 线均无法进入暴打陈敏！")
    return False


def check_can_beat_chen(context: Context) -> bool:
    """
    检测当前是否已经进入暴打陈敏游戏
    """
    img = context.tasker.controller.post_screencap().wait().get()
    try:
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
            return True
        else:
            return False
    finally:
        del img
