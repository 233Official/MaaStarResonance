from __future__ import annotations

import time
import traceback
from functools import wraps
from typing import Any, Callable

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, Rect
from maa.custom_action import CustomAction

from key_event import ANDROID_KEY_EVENT_DATA
from logger import logger

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
                img = context.tasker.controller.post_screencap().wait().get()
                is_main_page: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
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
            logger.exception(f"ReturnMainPageAction failed, error: {exc}\n{stack_trace}")
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
			try:
				for _ in range(max_retry):
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
					time.sleep(max(0.0, float(interval_sec)))
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

			return fn(self, context, *args, **kwargs)

		return wrapper

	return decorator


