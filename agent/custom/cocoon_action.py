import time

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.attach.common_attach import get_need_cocoon_name
from agent.constant.map_point import NAVIGATE_DATA
from agent.custom.general.move_battle import mount_vehicle, auto_attach
from agent.custom.general.power_saving_mode import exit_power_saving_mode
from agent.custom.general.world_line_switcher import switch_line
from agent.custom.teleport_action import teleport_or_navigate
from agent.logger import logger


@AgentServer.custom_action("CocoonAction")
class CocoonActionAction(CustomAction):

    @exit_power_saving_mode()
    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        """
        幻觉值不为空 -> 确保自动战斗；幻觉值为空 -> 关闭自动战斗后识别进茧再开自动战斗

        Args:
            context: 控制器上下文
            _: 其他

        Returns:
            任务执行结果
        """

        # 获取需要刷的茧的名字
        cocoon_name = get_need_cocoon_name(context)
        # 传送到目的位置
        teleport_or_navigate(context, None, cocoon_name, "导航", NAVIGATE_DATA)
        # 点击按钮下马
        mount_vehicle(context, mount_type=0)

        # 确保到达茧的入口
        need_next = ensure_cocoon_entry(context)
        if not need_next:
            return False

        # 尝试切换到一条靠前的分线
        switch_line(context, ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])

        # 确保自动战斗关闭
        auto_attach(context, attack_type=0)

        # 点击进入茧
        context.tasker.controller.post_click(0, 0)  # TODO 进茧按钮坐标
        logger.info("初次进入茧，等待 5 秒后开始识别幻觉值并自动战斗")
        time.sleep(5)

        # 循环检测
        while not context.tasker.stopping:
            # 检测幻觉值
            img = context.tasker.controller.post_screencap().wait().get()
            ocr_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {
                        "expected": "[0-9]+",
                        "roi": [0, 0, 0, 0],  # TODO 幻觉值识别坐标
                    }
                },
            )
            if not ocr_result:
                return False

            if ocr_result.hit:
                # 有幻觉值，需要确保自动战斗还开着
                auto_attach(context, attack_type=1)
            else:
                # 没有幻觉值，需要关闭自动战斗后识别进茧再开自动战斗
                auto_attach(context, attack_type=0)
                # 检测还有没有按钮
                has_entry = ensure_cocoon_entry(context, 10)
                if has_entry:
                    # 点击进入茧
                    context.tasker.controller.post_click(0, 0)  # TODO 进茧按钮坐标
                else:
                    # 没有按钮，可能是位置发生偏移，尝试复位，战斗中不能导航，所以先传送
                    teleport_or_navigate(context, None, cocoon_name, "传送", NAVIGATE_DATA)
                    time.sleep(3)
                    # 再进行导航
                    teleport_or_navigate(context, None, cocoon_name, "导航", NAVIGATE_DATA)
                    # 确保到达茧的入口
                    need_next = ensure_cocoon_entry(context)
                    if not need_next:
                        return False
                    # 击按钮下马
                    mount_vehicle(context, mount_type=0)
                    # 点击进入茧
                    context.tasker.controller.post_click(0, 0)  # TODO 进茧按钮坐标
            # 10秒检查一次
            logger.info("已再次进入茧，等待 10 秒后开始识别幻觉值并自动战斗")
            time.sleep(10)
        return True


def ensure_cocoon_entry(context: Context, timeout: int = 120) -> bool:
    """确保到达茧的入口"""
    start_time = time.time()
    elapsed_time = 0
    # 循环检测是否到达茧的入口
    while elapsed_time <= timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img = context.tasker.controller.post_screencap().wait().get()
        is_arrive = context.run_recognition("检测是否到达茧的入口", img)
        if is_arrive and is_arrive.hit:
            del is_arrive, img
            logger.info(f"检测到已经到达茧的入口！")
            return True
        del is_arrive, img
        time.sleep(2)
    logger.error("超 120 秒未到达茧的入口！")
    return False
