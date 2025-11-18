import time
import traceback

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.custom_param import CustomActionParam
from logger import logger


# 自动钓鱼任务
@AgentServer.custom_action("AutoFishing")
class AutoFishingAction(CustomAction):

    def __init__(self):
        super().__init__()
        # 当前钓鱼次数
        self.fishing_count = 1
        # 成功钓鱼次数
        self.success_fishing_count = 0
        # 收竿触控通道常量
        self.REEL_IN_CONTACT = 0
        # 方向触控通道常量
        self.BOWING_CONTACT = 1

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        """
        超究极无敌变异进化全自动钓鱼：
        1. 可在钓鱼点上 或者 钓鱼界面 开始本任务，无需关心省电模式
        2. 已有鱼竿/鱼饵，会自动使用第一个，如果用完了会自动执行购买，鱼竿只买1个，鱼饵买200个
        3. 自动无限钓鱼不会停止，除非遇到意外情况
        4. 等待鱼鱼上钩最长等待30秒

        Args:
            context: 控制器上下文
            argv: 运行参数
                - max_success_fishing_count: 需要的最大成功钓鱼数量，默认设置0为无限钓鱼

        Returns:
            钓鱼结果：True / False
        """

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_success_fishing_count = int(params.data["max_success_fishing_count"]) if params.data["max_success_fishing_count"] else 0
        logger.info(f"本次任务设置的最大钓到的鱼鱼数量: {max_success_fishing_count}")

        # 开始钓鱼循环
        while self.check_running(context):
            # 检查是否已经钓到足够数量的鱼鱼了
            if max_success_fishing_count != 0 and max_success_fishing_count <= self.success_fishing_count:
                logger.info(f"[任务结束] 已成功钓到了您所配置的{self.success_fishing_count}条鱼鱼，自动钓鱼结束！")
                return True
            
            # 1. 判断省电模式 | 失败也不要紧，说明不在省电模式
            context.run_action("从省电模式唤醒")
            time.sleep(1)

            # 钓鱼主循环
            logger.info(f"===> 开始第{self.fishing_count}次钓鱼 | 累计已成功{self.success_fishing_count}条 <===")
            self.fishing_count += 1

            try:
                # 2.1 检测进入钓鱼按钮
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                fishing_result: RecognitionDetail | None = context.run_recognition("检测进入钓鱼按钮", img)
                if fishing_result and fishing_result.hit:
                    logger.info("[任务准备] 正在进入钓鱼台，等待5秒...")
                    context.run_action("点击进入钓鱼按钮")
                    time.sleep(5)
                    # 识别出了：走进钓鱼台，并重新截图
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                else:
                    logger.warning('[任务准备] 没有检测到进入钓鱼台按钮，可能是已经在钓鱼中，将直接检测抛竿按钮')

                # 2.2 检测抛竿按钮
                reeling_result: RecognitionDetail | None = context.run_recognition("检测抛竿按钮", img)
                if reeling_result and not reeling_result.hit:
                    logger.warning('[任务准备] 没有检测到抛竿按钮，可能是遇到掉线/切线情况')
                    
                    # 2.3 检查其他意外情况
                    disconnect_result: RecognitionDetail | None = context.run_recognition(
                        "通用文字识别",
                        img,
                        pipeline_override={
                            "通用文字识别": {"expected": "确认", "roi": [767, 517, 59, 27]}
                        },
                    )
                    if disconnect_result and disconnect_result.hit:
                        # 有确认按钮：很有可能是掉线了
                        logger.info("[任务准备] 检测到掉线重连按钮，正在点击重连，等待30秒后重试...")
                        context.tasker.controller.post_click(797, 532).wait()
                    else:
                        # 可能是：分线过期自动切线、月卡弹窗、广告弹窗  | TODO：广告弹窗暂不支持处理
                        logger.warning("[任务准备] 未检测到掉线重连按钮，可能是自动切线或月卡弹窗，自动处理后等待30秒后重试...")
                        context.tasker.controller.post_click(640, 10).wait()
                    del disconnect_result, fishing_result, reeling_result, img
                    # 等待30秒后直接进入下个循环
                    time.sleep(30)
                    continue
                
                del fishing_result, reeling_result, img
                time.sleep(3)

                # 3.1 检测配件：鱼竿
                self.ensure_equipment(
                    context,
                    "鱼竿",
                    add_task="检测是否需要添加鱼竿",
                    add_action="点击添加鱼竿",
                    buy_task="检测是否需要购买鱼竿",
                    buy_actions=[
                    "点击前往购买鱼竿页面",
                    "选择并购买需要的鱼竿",
                    "点击钓鱼配件购买按钮"
                    ],
                    use_action="点击使用鱼竿"
                )

                # 3.2 检测配件：鱼饵
                self.ensure_equipment(
                    context,
                    "鱼饵",
                    add_task="检测是否需要添加鱼饵",
                    add_action="点击添加鱼饵",
                    buy_task="检测是否需要购买鱼饵",
                    buy_actions=[
                    "点击前往购买鱼饵页面",
                    "选择并购买需要的鱼饵",
                    "点击钓鱼配件最大数量按钮",
                    "点击钓鱼配件购买按钮",
                    "点击确认购买按钮"
                    ],
                    use_action="点击使用鱼饵"
                )
                
                # 4. 开始抛竿
                logger.info("[任务准备] 开始抛竿，等待鱼鱼上钩...")
                context.run_action("点击抛竿按钮")
                time.sleep(1)

                # 5. 检测鱼鱼是否上钩 | 检测30秒，检测时间长，如果有中断命令就直接结束
                need_next = True
                wait_for_fish_times = 0
                while wait_for_fish_times < 300:
                    if not self.check_running(context):
                        need_next = False
                        break
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    is_hooked: RecognitionDetail | None = context.run_recognition("检测鱼鱼是否上钩", img)
                    if is_hooked and is_hooked.hit:
                        del is_hooked, img
                        logger.info("[执行钓鱼] 鱼鱼上钩了！")
                        break
                    time.sleep(0.1)
                    wait_for_fish_times += 1
                # 30秒检测内如果没有下一次了，说明钓鱼被强制结束了
                if not need_next:
                    break

                # 6. 开始收线循环
                need_next = self.reel_loop(context)
                # 没有下一次了，说明钓鱼被强制结束了
                if not need_next:
                    break
                time.sleep(4)

                # 7. 本次钓鱼完成，再次检测并点击继续钓鱼按钮进行第二次钓鱼
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
                if is_continue_fishing and is_continue_fishing.hit:
                    self.success_fishing_count += 1
                    logger.info("[执行钓鱼] 成功钓上了鱼鱼，将开始下一轮钓鱼")
                    time.sleep(1)
                    context.run_action("点击继续钓鱼按钮")
                del is_continue_fishing, img
                time.sleep(2)

            except Exception as exc:
                stack_trace = traceback.format_exc()
                logger.exception(f"[任务结束] 自动钓鱼出现未知错误: {exc}\n{stack_trace}",)
                return False

        logger.warning("[任务结束] 自动钓鱼已结束！")
        return True
    
    @staticmethod
    def ensure_equipment(
        context: Context,
        type_str: str,
        add_task: str,
        add_action: str,
        buy_task: str,
        buy_actions: list[str],
        use_action: str
    ) -> None:
        """
        检查钓鱼配件
        """
        # 1. 检测添加按钮
        img = context.tasker.controller.post_screencap().wait().get()
        det = context.run_recognition(add_task, img)
        if not det or not det.hit:
            return
        logger.info(f"[任务准备] 检测到需要添加{type_str}")

        # 2. 点击添加按钮
        context.run_action(add_action)
        time.sleep(2)

        # 3. 检测是否需要购买，如果需要就购买
        img = context.tasker.controller.post_screencap().wait().get()
        need_buy = context.run_recognition(buy_task, img)
        if need_buy and need_buy.hit:
            logger.info(f"[任务准备] 检测到{type_str}不足，需要购买")
            # 执行一连串购买步骤
            for act in buy_actions:
                context.run_action(act)
                time.sleep(2)
            logger.info(f"[任务准备] {type_str}购买完成，将退回钓鱼界面")
            # 购买完回到钓鱼界面
            context.run_action("ESC")
            time.sleep(2)
            # 再次检测和点击添加按钮
            img = context.tasker.controller.post_screencap().wait().get()
            context.run_recognition(add_task, img)
            context.run_action(add_action)
            time.sleep(2)

        # 4. 使用配件
        logger.info(f"[任务准备] 点击使用已有的{type_str}")
        context.run_action(use_action)
        time.sleep(2)

    def reel_loop(self, context: Context) -> bool:
        """
        钓鱼循环逻辑：
        1. 初始状态 -> 收线键：${press_duration_reel}秒后停${release_duration_reel}秒，保持该节奏循环；方向键：不动
        2. 首次识别箭头方向 -> 收线键：立即重置循环上述节奏循环；方向键：按压${press_duration_bow}秒后松开
        3. 循环模式中再次出现箭头：
           - 冷却期未到 -> 不改变之前两个按键的状态
           - 同方向 -> 不改变之前两个按键的状态
           - 不同方向 -> 收线键：立即重置循环上述节奏循环；方向键：换对应方向按压${press_duration_bow}秒后松开
        4. 每${loop_interval}循环一次，根据循环独立判断收线键和方向键，以便两个按键同时操作且不堵塞
        """

        # ========== 可配置参数 ==========
        press_duration_reel = 2.8  # 收线按压时长
        release_duration_reel = 0.2  # 收线松开时长 | 收线松开时长 >= 循环检测间隔
        press_duration_bow = 2.8  # 方向按压时长
        loop_interval = 0.1  # 循环检测间隔 | 太短影响性能，太长影响收线
        arrow_cooldown = 0.5  # 箭头方向冷却时间（秒），冷却期内不再检测

        # ========== 状态变量 ==========
        is_reel_pressed = False  # 当前收线键状态
        cycle_start_time = None  # 节奏循环开始时间
        last_arrow_direction = None  # 最近确认的箭头方向
        is_bow_pressed = False  # 当前方向键状态
        bow_release_time = 0  # 当前方向松开的时间
        arrow_last_detect_time = 0  # 上次确认箭头的时间戳

        while self.check_running(context):
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()

            # 检查是否还在收线
            if not self.check_if_reeling(context, img):
                logger.info("[执行钓鱼] 当前已不在收线状态，等待一会检测继续钓鱼按钮...")
                del img
                if is_reel_pressed:
                    self.stop_reel_in(context)
                if is_bow_pressed:
                    self.stop_bow(context)
                return True

            now = time.time()

            # 冷却期内跳过箭头检测
            if now - arrow_last_detect_time >= arrow_cooldown:
                confirmed_arrow = self.get_bow_direction(context, img)
            else:
                confirmed_arrow = None

            del img

            # ===== 收线逻辑 =====
            if cycle_start_time is None and confirmed_arrow is None:
                # 初始无箭头 -> 进行常规收线节奏
                if not is_reel_pressed:
                    self.start_reel_in(context)
                    is_reel_pressed = True
                cycle_start_time = now

            elif confirmed_arrow is not None and last_arrow_direction is None:
                # 首次确认箭头方向 -> 停一下进入循环模式
                if is_reel_pressed:
                    self.stop_reel_in(context)
                    is_reel_pressed = False
                cycle_start_time = now
                last_arrow_direction = confirmed_arrow
                arrow_last_detect_time = now
                logger.info(f"[执行钓鱼] 首次箭头方向确认：{confirmed_arrow} -> 开始循环模式")

                # 按方向键
                if self.start_bow(context, confirmed_arrow):
                    is_bow_pressed = True
                    bow_release_time = now + press_duration_bow

            elif confirmed_arrow is not None:
                if confirmed_arrow != last_arrow_direction:
                    # 不同方向 -> 停一下再进入循环
                    if is_reel_pressed:
                        self.stop_reel_in(context)
                        is_reel_pressed = False
                    time.sleep(release_duration_reel)
                    cycle_start_time = time.time()
                    last_arrow_direction = confirmed_arrow
                    arrow_last_detect_time = now
                    logger.info(f"[执行钓鱼] 方向变化为 {confirmed_arrow} -> 重置循环模式")
                # 按方向键
                if self.start_bow(context, confirmed_arrow):
                    is_bow_pressed = True
                    bow_release_time = now + press_duration_bow

            # 收线节奏控制
            if cycle_start_time is not None:
                elapsed = (now - cycle_start_time) % (press_duration_reel + release_duration_reel)
                if elapsed < press_duration_reel:
                    if not is_reel_pressed:
                        self.start_reel_in(context)
                        is_reel_pressed = True
                else:
                    if is_reel_pressed:
                        self.stop_reel_in(context)
                        is_reel_pressed = False

            # ===== 方向键松开控制 =====
            if is_bow_pressed and now >= bow_release_time:
                self.stop_bow(context)
                is_bow_pressed = False

            time.sleep(loop_interval)
        return False

    @staticmethod
    def check_if_reeling(context: Context, img: numpy.ndarray) -> bool:
        """
        检查当前是否在收线：
        1. 钓到鱼鱼了：检测继续钓鱼按钮
        2. 鱼鱼跑路了：检测是否在抛竿界面
        """
        recognition_task: RecognitionDetail | None = context.run_recognition("检测是否在抛竿界面", img)
        is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)

        # 有任何一个检测到了说明就不在收线了
        in_reel = True
        if (recognition_task and recognition_task.hit) or (is_continue_fishing and is_continue_fishing.hit):
            in_reel = False
        del recognition_task, is_continue_fishing
        return in_reel

    @staticmethod
    def get_bow_direction(context: Context, img: numpy.ndarray, score_threshold: float = 0.6,
                          min_score_diff: float = 0.05) -> str | None:
        """
        获取箭头方向（'left' / 'right' / None）带分数阈值：
        1. 左右箭头分数低于 score_threshold 视为无效
        2. 分数差小于 min_score_diff，则视为无效（避免接近分数误判）
        3. 返回方向字符串或 None
        """
        bow_left_task: RecognitionDetail | None = context.run_recognition("检查向左箭头", img)
        bow_right_task: RecognitionDetail | None = context.run_recognition("检查向右箭头", img)

        if not bow_left_task and not bow_right_task:
            return None

        bow_left_score = bow_left_task.best_result.score if (bow_left_task and bow_left_task.best_result) else 0.0  # type: ignore
        bow_right_score = bow_right_task.best_result.score if (bow_right_task and bow_right_task.best_result) else 0.0  # type: ignore

        # logger.debug(f"[箭头识别] 左分数: {bow_left_score:.3f}, 右分数: {bow_right_score:.3f}")

        # 阈值过滤
        if bow_left_score < score_threshold and bow_right_score < score_threshold:
            del bow_left_score, bow_right_score, bow_left_task, bow_right_task
            return None

        # 差异过滤
        if abs(bow_left_score - bow_right_score) < min_score_diff:
            del bow_left_score, bow_right_score, bow_left_task, bow_right_task
            return None

        bow_direction = None
        if bow_left_score >= score_threshold and bow_left_score > bow_right_score:
            bow_direction = "left"
        elif bow_right_score >= score_threshold and bow_right_score > bow_left_score:
            bow_direction = "right"
        del bow_left_score, bow_right_score, bow_left_task, bow_right_task
        return bow_direction

    def start_reel_in(self, context: Context) -> bool:
        """
        开始收线动作
        """
        result = context.tasker.controller.post_touch_down(1160, 585, self.REEL_IN_CONTACT, 1).wait()
        return result.succeeded

    def stop_reel_in(self, context: Context) -> bool:
        """
        停止收线动作
        """
        result = context.tasker.controller.post_touch_up(self.REEL_IN_CONTACT).wait()
        return result.succeeded

    def start_bow(self, context: Context, direction: str) -> bool:
        """
        开始箭头转向动作
        """
        x = 150 if direction == "left" else 320
        y = 530
        result = context.tasker.controller.post_touch_down(x, y, self.BOWING_CONTACT, 1).wait()
        return result.succeeded

    def stop_bow(self, context: Context) -> bool:
        """
        停止箭头转向动作
        """
        result = context.tasker.controller.post_touch_up(self.BOWING_CONTACT).wait()
        return result.succeeded

    @staticmethod
    def check_running(context: Context) -> bool:
        """
        检查任务是否正在被停止 | 钓鱼有三个循环，理论上最多触发5次停止事件就会停下了
        """
        if context.tasker.stopping:
            logger.info("[任务结束] 监听到自动钓鱼任务被结束，将结束循环，请耐心等待一小会")
            return False
        return True
