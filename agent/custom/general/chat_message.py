import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.attach.common_attach import get_chat_message_content, get_chat_channel_id_list
from agent.constant.world_channel import CHANNEL_DATA
from agent.logger import logger


# 发送聊天频道消息
@AgentServer.custom_action("SendMessage")
class SendMessageAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        return send_message(context)


def send_message(context: Context) -> bool:
    # 本轮成功次数
    success_count = 0

    # 0. 变量检查
    message_content = get_chat_message_content(context)
    if not message_content:
        logger.error("需要发送的消息内容为空，请先设置内容")
        return False
    logger.info(f"需要发送的消息内容为: {message_content}")

    channel_id_list = get_chat_channel_id_list(context)
    if not channel_id_list:
        logger.error("需要发送的世界频道分线列表为空，请先设置分线")
        return False
    logger.info(f"需要发送的世界频道分线列表为: {str(channel_id_list)}")

    # 1. 检测并打开聊天框
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    chat_button: RecognitionDetail | None = context.run_recognition("检测聊天按钮", img)
    if not chat_button or not chat_button.hit:
        logger.error("未检测到聊天按钮，无法发送消息")
        return False
    context.tasker.controller.post_click(480, 600)

    # 2. 切换到世界频道

    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    world_chat: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "世界", "roi": [29, 43, 160, 138]}
        },
    )
    if not world_chat or world_chat.hit:
        logger.error("未检测到世界频道，无法发送消息")
        context.run_action("ESC")
        return False
    context.tasker.controller.post_click(110, 110)

    # 根据世界频道分线ID列表循环处理
    for channel_id in channel_id_list:
        # 3. 切换世界频道分线
        time.sleep(2)
        need_next = change_channel(channel_id, context)
        if not need_next:
            continue
        # 4. 点击输入框
        time.sleep(1)
        context.tasker.controller.post_click(190, 680)
        # 5. 输入内容
        time.sleep(1)
        context.run_action("输入聊天框内容", pipeline_override={
            "输入聊天框内容": {
                "action": {
                    "type": "InputText",
                    "param": {
                        "input_text": message_content
                    }
                }
            }
        })
        # 6. 点击确定按钮
        time.sleep(1)
        context.tasker.controller.post_click(1210, 670)
        # 7. 检测并点击发送图标
        time.sleep(1)
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        send_button: RecognitionDetail | None = context.run_recognition("检测发送消息按钮", img)
        if send_button and send_button.hit:
            context.tasker.controller.post_click(810, 666)
            success_count += 1
            logger.info(f"已成功向聊天世界频道 {channel_id} 发送消息内容")
        else:
            logger.error(f"向聊天世界频道 {channel_id} 发送消息内容失败：识别不到发送按钮")

    logger.info(f"===== 本轮发送世界频道消息已经成功：{success_count} / {len(channel_id_list)} ====")
    return True


def change_channel(channel_id: str, context: Context, interval: float = 0.5) -> bool:
    """
    根据 channel_id 切换频道

    Args:
        channel_id:
        context: 控制器上下文
        interval: 每次按键之间的间隔秒数，默认 0.5

    Returns:
        切换成功与否
    """
    # 输入
    for digit in channel_id:
        if digit not in CHANNEL_DATA:
            continue
        x, y = CHANNEL_DATA[digit]
        context.tasker.controller.post_click(x, y)
        time.sleep(interval)
    # 切换
    time.sleep(1)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    switch_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "OK", "roi": [286, 142, 146, 131]}
        },
    )
    if switch_result and switch_result.hit:
        logger.info(f"已成功切换到聊天世界频道: {channel_id}")
        return True

    # TODO 后续需要校验是否真的切换成功，需要根据原来所在分线判断
    logger.info(f"聊天世界频道: {channel_id} 切换失败")
    return False
