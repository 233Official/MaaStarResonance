from logger import logger
import traceback
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction

from custom_param import CustomActionParam, CustomActionParamError
from key_event import ANDROID_KEY_EVENT_DATA


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

        judge_detail = context.run_recognition(
            entry=judge_node,
            image=argv.reco_detail.raw_image,
        )
        logger.debug(f"[DecisionRouterAction] judge_detail: {judge_detail}")
        # 匹配失败的话 judge_detail 会是 None, 否则会是 RecognitionDetail 对象
        judge_succeeded = bool(judge_detail)

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
