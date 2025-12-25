import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.logger import logger


# 关闭所有广告
@AgentServer.custom_action("CloseAd")
class CloseAdAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        return close_ad(context)

def close_ad(context: Context) -> bool:
    """
    关闭所有广告

    Args:
        context: 控制器上下文

    Returns: 是否完成

    """
    # 检测今日不再弹出按钮
    while not context.tasker.stopping:
        # 展示太慢了，等5秒
        logger.info("开始检测并关闭可能的广告弹窗")
        time.sleep(5)
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        firm_result: RecognitionDetail | None = context.run_recognition("检测今日不再弹出按钮", img)
        if not firm_result:
            logger.warning("广告弹窗检测不可达！")
            return True
        if firm_result.hit:
            logger.info("检测到弹窗广告，准备关闭广告...")
            # 点击不再弹出按钮
            context.tasker.controller.post_click(263, 609).wait()
            time.sleep(1)
            # 点击关闭广告按钮
            context.tasker.controller.post_click(1061, 157).wait()
            time.sleep(1)
        else:
            # 检测不到广告
            return True

    return True
