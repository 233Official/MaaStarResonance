import time
import traceback

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, Rect
from maa.custom_action import CustomAction
from rapidfuzz import fuzz

from custom_param import CustomActionParam, CustomActionParamError
from key_event import ANDROID_KEY_EVENT_DATA
from logger import logger
from map_point import MAP_POINT_DATA


@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        logger.info("my_action_111 is running!")
        return True


# 运行任务流水线任务
@AgentServer.custom_action("run_pipeline_node")
class RunTaskPipelineAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        params: CustomActionParam | None = None
        pipeline_node_name = ""
        try:
            params = CustomActionParam(argv.custom_action_param)
            required = params.require(["pipeline_node_name"])
            pipeline_node_name = required["pipeline_node_name"]
            logger.info(f"pipeline_node_name: {pipeline_node_name}")
            context.run_task(entry=pipeline_node_name)
            logger.success(f"run pipeline node {pipeline_node_name} success")
            return True
        except CustomActionParamError as exc:
            logger.error(f"run pipeline node 参数错误: {exc}")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            if not pipeline_node_name and params:
                pipeline_node_name = params.data.get("pipeline_node_name", "")
            logger.exception(
                f"run pipeline node {pipeline_node_name} failed, error: {exc}\n{stack_trace}",
            )
            return False


# 条件判断分支
@AgentServer.custom_action("decision_router")
class DecisionRouterAction(CustomAction):
    """根据判断节点结果决定后续节点"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """根据判断节点结果决定后续节点

        Args:
            context (Context): 上下文对象
            argv (CustomAction.RunArg): 自定义动作参数
                具体参数格式: {"judge_node": "判断节点名称", "success_node": "成功节点名称", "failure_node": "失败节点名称"}
        Returns:
            CustomAction.RunResult: 运行结果
        """
        logger.debug(f"argv: {argv}")
        try:
            parser = CustomActionParam(argv.custom_action_param)
            params = parser.require(("judge_node", "success_node", "failure_node"))
        except CustomActionParamError as exc:
            logger.error(f"[DecisionRouterAction] 参数解析失败: {exc}")
            return CustomAction.RunResult(success=False)
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            logger.exception(
                f"[DecisionRouterAction] 参数解析异常: {exc}\n{stack_trace}",
            )
            return CustomAction.RunResult(success=False)

        judge_node = params["judge_node"]
        success_node = params["success_node"]
        failure_node = params["failure_node"]

        # judge_detail = context.run_task(judge_node)
        # if judge_detail and judge_detail.nodes:
        #     judge_succeeded = True
        # else:
        #     judge_succeeded = False

        judge_detail: RecognitionDetail | None = context.run_recognition(
            entry=judge_node,
            image=argv.reco_detail.raw_image,
        )
        logger.debug(f"[DecisionRouterAction] judge_detail: {judge_detail}")
        # 匹配失败的话 RecognitionDetail.hit: bool 会是 False
        judge_succeeded = judge_detail and judge_detail.hit

        target_node = success_node if judge_succeeded else failure_node
        logger.debug(f"[DecisionRouterAction] target_node: {target_node}")
        if not target_node:
            logger.warning("[DecisionRouterAction] 目标节点为空")
            return CustomAction.RunResult(success=False)

        logger.debug(f"argv.node_name: {argv.node_name}")
        current_node = argv.node_name
        # override_result = context.override_pipeline({argv.node_name: {"next": [target_node]}})
        # override_result = context.override_next(argv.node_name, [target_node])
        override_result = context.override_next(current_node, [target_node])
        if not override_result:
            logger.error(f"[DecisionRouterAction] override_pipeline 失败")
            return CustomAction.RunResult(success=False)
        return CustomAction.RunResult(success=True)

        # target_node_run_detail = context.run_task(entry=target_node)
        # logger.debug(f"[DecisionRouterAction] target_node_run_detail: {target_node_run_detail}")
        # if target_node_run_detail and target_node_run_detail.status:
        #     return CustomAction.RunResult(success=True)

        # return CustomAction.RunResult(success=False)


# 等待x秒
@AgentServer.custom_action("wait_x_seconds")
class WaitXSecondsAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        params: CustomActionParam | None = None
        wait_seconds = 0
        try:
            params = CustomActionParam(argv.custom_action_param)
            required = params.require(["wait_seconds"])
            wait_seconds = int(required["wait_seconds"])
            total = max(0, wait_seconds)
            if total <= 0:
                logger.warning("等待秒数 <= 0，跳过等待")
                return True

            # 计算打印进度的间隔：
            # - x <= 10: 每 1 秒
            # - 10 < x < 100: 每 10 秒
            # - 100 < x < 1000: 每 100 秒
            # - 以此类推（间隔为小于 x 的最大 10 的幂）
            def calc_interval(x: int) -> int:
                if x <= 10:
                    return 1
                step = 10
                while step * 10 < x:
                    step *= 10
                return step

            interval = calc_interval(total)
            if interval == 1:
                logger.info(f"开始等待 {total} 秒（每秒打印一次）")
                for remaining in range(total, 0, -1):
                    logger.info(f"剩余 {remaining} 秒…")
                    time.sleep(1)
            else:
                logger.info(
                    f"开始等待 {total} 秒（每 {interval} 秒打印一次进度）"
                )
                elapsed = 0
                while elapsed + interval < total:
                    time.sleep(interval)
                    elapsed += interval
                    logger.info(f"已等待 {elapsed}/{total} 秒")

                # 补齐最后不足一个间隔的时间
                remaining = total - elapsed
                if remaining > 0:
                    time.sleep(remaining)

            logger.success(f"已等待 {total} 秒")
            return True
        except CustomActionParamError as exc:
            logger.error(f"WaitXSecondsAction 参数错误: {exc}")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            if params:
                wait_seconds = params.data.get("wait_seconds", 0)
            logger.exception(
                f"WaitXSecondsAction 等待 {wait_seconds} 秒失败, 错误: {exc}\n{stack_trace}",
            )
            return False


# 运行一系列自定义动作
@AgentServer.custom_action("run_custom_actions_series")
class RunCustomActionsSeriesAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        params: CustomActionParam | None = None
        actions: list[str] = []
        interval: int = 1000  # 默认动作衔接等待时间为1000毫秒
        try:
            params = CustomActionParam(argv.custom_action_param)
            required = params.require(["actions", "interval"])
            actions = required["actions"]
            interval = int(required["interval"])
            logger.debug(
                f"Running custom actions series: {actions} with interval {interval} ms"
            )

            for action_name in actions:
                context.run_action(entry=action_name)
                time.sleep(interval / 1000)

            logger.success(f"成功运行自定义动作系列: {actions}")
            return True
        except CustomActionParamError as exc:
            logger.error(f"RunCustomActionsSeriesAction 参数错误: {exc}")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            if params:
                actions = params.data.get("actions", [])
                interval = params.data.get("interval", 1000)
            logger.exception(
                f"RunCustomActionsSeriesAction 运行自定义动作系列 {actions} 失败, 错误: {exc}\n{stack_trace}",
            )
            return False


# 向前(W)/后(S)/左(A)/右(D)移动second秒
@AgentServer.custom_action("move_wsad")
class MoveWSADAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        params: CustomActionParam | None = None
        direction: str = ""
        millisecond: int = 0
        try:
            params = CustomActionParam(argv.custom_action_param)
            required = params.require(["direction", "millisecond"])
            direction = required["direction"]
            millisecond = int(required["millisecond"])

            key_map = {
                "前": "KEYCODE_W",
                "左": "KEYCODE_A",
                "后": "KEYCODE_S",
                "右": "KEYCODE_D",
            }
            key_name = key_map.get(direction)
            key_code = ANDROID_KEY_EVENT_DATA.get(key_name)
            if not key_code:
                raise ValueError(f"Invalid direction: {direction}")

            logger.debug(
                f"尝试向{direction}移动 {millisecond} 毫秒, key_code: {key_code}, duration: {millisecond} ms"
            )
            # 按下按键millisecond毫秒后松开
            context.run_task(
                entry="按住W键1秒",
                pipeline_override={
                    "按住W键1秒": {
                        "action": {
                            "param": {"key": key_code, "duration": millisecond},
                        }
                    }
                },
            )

            logger.success(f"向{direction}移动 {millisecond} 毫秒成功")
            return True
        except CustomActionParamError as exc:
            logger.error(f"MoveWSADAction 参数错误: {exc}")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            if params:
                direction = params.data.get("direction", "")
                millisecond = params.data.get("millisecond", 0)
            logger.exception(
                f"MoveWSADAction 移动 {direction} {millisecond} 毫秒失败, 错误: {exc}\n{stack_trace}",
            )
            return False


@AgentServer.custom_action("TeleportPoint")
class TeleportPointAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        try:
            params = CustomActionParam(argv.custom_action_param)
            required = params.require(["dest_map", "dest_tele_point"])
            dest_map = required["dest_map"]
            dest_tele_point = required["dest_tele_point"]
            logger.info(f"dest_map: {dest_map}, dest_tele_point: {dest_tele_point}")

            # 1. 打开地图
            context.tasker.controller.post_click_key(
                ANDROID_KEY_EVENT_DATA["KEYCODE_M"]
            ).wait()
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

            # 4. OCR 搜索地图名字并点击
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
            rect = Rect(*item.box)  #type: ignore
            logger.info(f"dest_map: {rect}, {item.text}")  #type: ignore
            point_x = int(rect.x + rect.w / 2)
            point_y = int(rect.y + rect.h / 2)
            # 选择地图
            context.tasker.controller.post_click(point_x, point_y)
            time.sleep(2)

            # 5. 在目标传送点坐标点击
            if dest_map not in MAP_POINT_DATA:
                logger.exception(
                    f"暂不支持的地图：{dest_map}，可能是命名不同或暂未支持"
                )
                return False
            if dest_tele_point not in MAP_POINT_DATA[dest_map]:
                logger.exception(
                    f"暂不支持的传送点：{dest_map}-{dest_tele_point}，可能是命名不同或暂未支持"
                )
                return False
            xy = MAP_POINT_DATA[dest_map][dest_tele_point]
            floor_xy = xy.get("floor", {})
            # 有楼层坐标 | 说明可能有上下几层的，需要先切换楼层
            if floor_xy:
                context.tasker.controller.post_click(
                    floor_xy["x"], floor_xy["y"]
                ).wait()
                time.sleep(2)
            # 点击传送点坐标
            context.tasker.controller.post_click(xy["x"], xy["y"]).wait()
            time.sleep(2)

            # 6. 判断是否可以直接传送
            img = context.tasker.controller.post_screencap().wait().get()
            is_direct_tp: RecognitionDetail | None = context.run_recognition(
                "图片识别传送点是否可以直接传送", img
            )

            if is_direct_tp and not is_direct_tp.hit:
                # 6.5 继续选择传送点
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
                    score = fuzz.ratio(item.text, alias)  #type: ignore
                    item.score = score  #type: ignore
                # 重新根据匹配分数排序
                sorted_items = sorted(
                    ocr_result.all_results, key=lambda obj: obj.score, reverse=True  #type: ignore
                )
                item = sorted_items[0]
                rect = Rect(*item.box)
                logger.info(f"dest_tele_point: {rect}, {item.text}")  #type: ignore
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

            print(f"传送[{dest_map}-{dest_tele_point}]完成")
            return True
        except CustomActionParamError as exc:
            logger.error(f"run pipeline node 参数错误: {exc}")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            logger.exception(f"TeleportPoint failed, error: {exc}\n{stack_trace}")
            return False
