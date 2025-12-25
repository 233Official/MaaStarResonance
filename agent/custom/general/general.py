from __future__ import annotations

import json
import time
import traceback
from functools import wraps
from typing import Any, Callable

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition

from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.logger import logger


# 返回主页面
@AgentServer.custom_action("return_main_page")
class ReturnMainPageAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        try:
            # 按返回键直到回到主页面，最多按10次防止死循环
            for _ in range(10):
                # 任务强制中止判断
                if context.tasker.stopping:
                    return False
                img = context.tasker.controller.post_screencap().wait().get()
                is_main_page: RecognitionDetail | None = context.run_recognition(
                    "图片识别是否在主页面", img
                )
                if is_main_page and is_main_page.hit:
                    logger.info("已回到主页面")
                    return True
                # 按返回键
                context.tasker.controller.post_click_key(
                    ANDROID_KEY_EVENT_DATA["KEYCODE_ESCAPE"]
                ).wait()
                time.sleep(1)
            logger.error("无法回到主页面，已达到最大尝试次数")
            return False
        except Exception as exc:  # pragma: no cover - 运行时保护
            stack_trace = traceback.format_exc()
            logger.exception(
                f"ReturnMainPageAction failed, error: {exc}\n{stack_trace}"
            )
            return False


def ensure_main_page(
    max_retry: int = 10,
    interval_sec: float = 1.0,
    strict: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """方法装饰器：在被装饰的方法执行前，确保回到游戏主页面。

    逻辑：截图 -> 识别“是否在主页面” -> 否则发送返回键 -> 重试，直到达成或超限。

    Args:
            max_retry: 最大重试次数（按返回键的最多次数）。
            interval_sec: 每次尝试之间的等待秒数。
            strict: True 时若最终仍未回到主页面则抛出异常；
                    False 时仅记录错误日志后继续执行被装饰的方法。

    Returns:
            被包装的方法。保持原返回值类型不变（bool 或 CustomAction.RunResult 等）。
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: CustomAction, context: Context, *args: Any, **kwargs: Any):
            # 填充默认确保主界面方法
            default_ensure_main_page(context, max_retry, interval_sec, strict)
            return fn(self, context, *args, **kwargs)

        return wrapper

    return decorator


def default_ensure_main_page(
        context: Context,
        max_retry: int = 10,
        interval_sec: float = 1.0,
        strict: bool = False
) -> None:
    """
    默认的确保主界面方法

    Args:
        context: 控制器上下文
        max_retry: 最大重试次数（按返回键的最多次数）。
        interval_sec: 每次尝试之间的等待秒数。
        strict: True 时若最终仍未回到主页面则抛出异常；
                False 时仅记录错误日志后继续执行被装饰的方法。

    Returns:
        None
    """
    try:
        for _ in range(max_retry):
            # 任务强制中止判断
            if context.tasker.stopping:
                break
            img = context.tasker.controller.post_screencap().wait().get()
            detail: RecognitionDetail | None = context.run_recognition(
                "图片识别是否在主页面", img
            )
            if detail and detail.hit:
                logger.info("[EnsureMainPage] 已在主页面")
                break
            context.tasker.controller.post_click_key(
                ANDROID_KEY_EVENT_DATA["KEYCODE_ESCAPE"]
            ).wait()
            time.sleep(max(0.0, interval_sec))
        else:
            # for 未被 break，达到最大次数
            msg = "[EnsureMainPage] 无法回到主页面，已达到最大尝试次数"
            if strict:
                logger.error(msg)
                raise RuntimeError(msg)
            logger.error(msg)
    except Exception as exc:  # pragma: no cover - 防御性保护
        logger.exception(f"[EnsureMainPage] 执行前置回主页面逻辑失败: {exc}")
        if strict:
            # 严格模式下失败直接中断
            raise


# 复合识别器：所有指定节点都识别成功才算成功
@AgentServer.custom_recognition("AllMatch")
class AllMatchRecognition(CustomRecognition):
    """
    复合识别器：所有指定节点都识别成功才算成功。

    参数格式 (custom_recognition_param):
        {
            "nodes": ["NodeA", "NodeB", "NodeC"],
        }

    返回值：
        成功时返回最后一个节点的识别框和详情
        任一失败则整体失败
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        # 解析参数
        try:
            params = json.loads(argv.custom_recognition_param)
            nodes: list[str] = params.get("nodes", [])
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"[AllMatch] 参数解析失败: {e}")
            return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})

        if not nodes:
            logger.error("[AllMatch] 节点列表为空")
            return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})
        # 用于存储最后一个成功的识别结果
        last_detail: RecognitionDetail | None = None

        # 当前使用的图像
        image = argv.image

        for i, node_name in enumerate(nodes):
            # 任务强制中止判断
            if context.tasker.stopping:
                return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})
            reco_detail = context.run_recognition(node_name, image, {})

            if reco_detail is None or reco_detail.box is None:
                # 任一节点识别失败，整体失败
                logger.error(f"[AllMatch] 节点 '{node_name}' 识别失败，终止")
                return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})

            # 记录结果
            last_detail = reco_detail

        logger.info(f"[AllMatch] 全部 {len(nodes)} 个节点识别成功")
        return CustomRecognition.AnalyzeResult(
            box=last_detail.box if last_detail else None,
            detail={'hit': True, 'detail': f'All {len(nodes)} nodes matched successfully'},
        )


# 复合识别器：任一指定节点识别成功即返回该节点结果
@AgentServer.custom_recognition("AnyMatch")
class AnyMatchRecognition(CustomRecognition):
    """任一节点识别成功即返回该节点结果"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        try:
            params = json.loads(argv.custom_recognition_param)
            nodes: list[str] = params.get("nodes", [])
        except (json.JSONDecodeError, TypeError):
            return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})

        for node_name in nodes:
            # 任务强制中止判断
            if context.tasker.stopping:
                return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})
            reco_detail = context.run_recognition(node_name, argv.image, {})
            if reco_detail and reco_detail.box is not None:
                detail = json.dumps(
                    {
                        "matched_node": node_name,
                        "box": list(reco_detail.box),
                    },
                    ensure_ascii=False,
                )
                return CustomRecognition.AnalyzeResult(
                    box=reco_detail.box,
                    detail={'hit': True,'detail': detail},
                )

        return CustomRecognition.AnalyzeResult(box=None, detail={'hit': False})
