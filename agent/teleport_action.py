import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, Rect
from maa.custom_action import CustomAction
from rapidfuzz import fuzz

from app_manage_action import get_area_change_timeout
from custom_param import CustomActionParam
from key_event import ANDROID_KEY_EVENT_DATA
from logger import logger
from map_point import MAP_POINT_DATA


@AgentServer.custom_action("TeleportPoint")
class TeleportPointAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        params = CustomActionParam(argv.custom_action_param)
        required = params.require(["dest_map", "dest_tele_point"])
        dest_map = required["dest_map"]
        dest_tele_point = required["dest_tele_point"]
        logger.info(f"目的地图: {dest_map}, 目的传送点: {dest_tele_point}")
        return teleport(context, dest_map, dest_tele_point)


def teleport(context: Context, dest_map: str, dest_tele_point: str) -> bool:
    """传送主方法"""
    area_change_timeout = get_area_change_timeout(context)

    # 1. 打开地图
    context.tasker.controller.post_click_key(ANDROID_KEY_EVENT_DATA["KEYCODE_M"]).wait()
    time.sleep(3)

    # 2. 是否已经打开地图了
    img = context.tasker.controller.post_screencap().wait().get()
    is_open_map: RecognitionDetail | None = context.run_recognition("图片识别是否已经打开地图", img)
    if not is_open_map or not is_open_map.hit:
        logger.exception("无法打开地图，请检查是否在剧情中或其他异常情况！")
        return False

    # 3. 点击左下角按钮展开地图
    context.tasker.controller.post_click(150, 666)
    time.sleep(1)

    # 4. OCR搜索地图名字并点击
    img = context.tasker.controller.post_screencap().wait().get()
    ocr_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": dest_map, "roi": [13, 288, 246, 341]}
        },
    )
    if not ocr_result or not ocr_result.hit:
        logger.exception("无法识别到地图名字！")
        return False
    # 获得最好结果坐标
    item = ocr_result.best_result
    rect = Rect(*item.box)  # type: ignore
    logger.info(f"dest_map: {rect}, {item.text}")  # type: ignore
    point_x = int(rect.x + rect.w / 2)
    point_y = int(rect.y + rect.h / 2)
    # 选择地图
    context.tasker.controller.post_click(point_x, point_y)
    time.sleep(2)

    # 5. 在目标传送点坐标点击
    if dest_map not in MAP_POINT_DATA:
        logger.exception(f"暂不支持的地图：{dest_map}，可能是命名不同或暂未支持")
        return False
    if dest_tele_point not in MAP_POINT_DATA[dest_map]:
        logger.exception(f"暂不支持的传送点：{dest_map}-{dest_tele_point}，可能是命名不同或暂未支持")
        return False

    xy = MAP_POINT_DATA[dest_map][dest_tele_point]
    floor_xy = xy.get("floor", {})
    # 有楼层坐标 | 说明可能有上下几层的，需要先切换楼层
    if floor_xy:
        context.tasker.controller.post_click(floor_xy["x"], floor_xy["y"]).wait()
        time.sleep(2)
    # 点击传送点坐标
    context.tasker.controller.post_click(xy["x"], xy["y"]).wait()
    time.sleep(2)

    # 6. 判断是否可以直接传送
    img = context.tasker.controller.post_screencap().wait().get()
    is_direct_tp: RecognitionDetail | None = context.run_recognition("图片识别传送点是否可以直接传送", img)
    if is_direct_tp and not is_direct_tp.hit:
        # 6.5 不能直接传送：继续选择传送点
        logger.info("没有传送按钮，可能是图标重合，继续选择")
        img = context.tasker.controller.post_screencap().wait().get()
        ocr_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {
                    "expected": "[\\S\\s]+",
                    "roi": [853, 207, 348, 311],
                }
            },
        )
        if not ocr_result or not ocr_result.hit:
            logger.exception(f"无法识别到传送点名字")
            return False

        # 匹配图标名优先用别称
        alias = xy.get("alias", dest_tele_point)
        # 重新用fuzzy匹配赋分 | 更安全更稳定，尤其是在背景可能变化的地图传送点这里
        for item in ocr_result.all_results:
            score = fuzz.ratio(item.text, alias)  # type: ignore
            item.score = score  # type: ignore
        # 重新根据匹配分数排序
        sorted_items = sorted(
            ocr_result.all_results, key=lambda obj: obj.score, reverse=True  # type: ignore
        )
        item = sorted_items[0]
        rect = Rect(*item.box)
        logger.info(f"dest_tele_point: {rect}, {item.text}")  # type: ignore
        point_x = int(rect.x + rect.w / 2)
        point_y = int(rect.y + rect.h / 2)
        # 选择传送点
        context.tasker.controller.post_click(point_x, point_y)
        time.sleep(2)
        # 再次判断是否可以直接传送
        img = context.tasker.controller.post_screencap().wait().get()
        is_direct_tp: RecognitionDetail | None = context.run_recognition(
            "图片识别传送点是否可以直接传送", img
        )
        if not is_direct_tp or not is_direct_tp.hit:
            logger.exception("传送失败：无法找到传送按钮")
            return False

    # 7. 点击传送按钮传送
    context.tasker.controller.post_click(1081, 656)
    logger.info(f"点击进行传送至 [{dest_map}：{dest_tele_point}] 等待传送完成...")

    # 等待进入游戏主页面
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            del area_change_result, img
            logger.info("检测到已经进入游戏主界面，传送完成！")
            return True
        del area_change_result, img
        time.sleep(2)

    # 超时未进入游戏主页面
    logger.error("传送超时，未检测到主页面，请检查应用状态！")
    return False
