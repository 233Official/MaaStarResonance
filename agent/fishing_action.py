import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from app_manage_action import restart_and_login_xhgm
from custom_param import CustomActionParam
from fish import FISH_LIST
from logger import logger
from utils import format_seconds_to_hms, get_best_match_single, print_center_block


# 自动钓鱼任务
@AgentServer.custom_action("AutoFishing")
class AutoFishingAction(CustomAction):

    def __init__(self):
        super().__init__()
        # 初始变量
        self.fishing_start_time = None
        self.fishing_count = None
        self.success_fishing_count = None
        self.except_count = None
        self.ssr_fish_count = None
        self.sr_fish_count = None
        self.r_fish_count = None
        self.used_rod_count = None
        self.used_bait_count = None
        self.restart_count = None

        # 收竿触控通道常量
        self.REEL_IN_CONTACT = 0
        # 方向触控通道常量
        self.BOWING_CONTACT = 1
        # 鱼鱼稀有度列表
        self.FISH_RARITY_LIST = ["常见", "珍稀", "神话"]
        # 鱼鱼名称列表
        self.FISH_NAME_LIST = FISH_LIST

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
        4. 等待鱼鱼咬钩最长等待30秒

        Args:
            context: 控制器上下文
            argv: 运行参数
                - max_success_fishing_count: 需要的最大成功钓鱼数量，默认设置0为无限钓鱼

        Returns:
            钓鱼结果：True / False
        """

        logger.warning(f"!!! 即将开始钓鱼，建议根据文档选择合适的钓鱼点 !!!")

        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        max_success_fishing_count = int(params.data["max_success_fishing_count"]) if params.data["max_success_fishing_count"] else 0
        # 获取是否重启游戏参数
        restart_for_except_node = context.get_node_data("获取参数-是否重启游戏")
        restart_for_except = restart_for_except_node.get("attach", {}).get("restart_for_except", True) if restart_for_except_node else True
        # 获取最大重启游戏次数限制参数
        max_restart_count_node = context.get_node_data("获取参数-最大重启游戏次数限制")
        max_restart_count = max_restart_count_node.get("attach", {}).get("max_restart_count", 5) if max_restart_count_node else 5
        # 打印参数信息
        logger.info(f"本次任务设置的最大钓到的鱼鱼数量: {max_success_fishing_count if max_success_fishing_count != 0 else '无限'}")
        logger.info(f"如遇到不可恢复异常，是否重启游戏: {'是' if restart_for_except else '否'}")

        # 当前时间
        now = time.time()
        
        # 起始钓鱼时间
        self.fishing_start_time = now
        # 累计钓鱼次数
        self.fishing_count = 0
        # 成功钓鱼次数
        self.success_fishing_count = 0
        # 出现意外次数
        self.except_count = 0
        # 神话鱼
        self.ssr_fish_count = 0
        # 珍稀鱼
        self.sr_fish_count = 0
        # 常见鱼
        self.r_fish_count = 0
        # 消耗的鱼竿数量
        self.used_rod_count = 0
        # 消耗的鱼饵数量
        self.used_bait_count = 0
        # 重启游戏次数
        self.restart_count = 0

        # 开始钓鱼循环
        while self.check_running(context):
            # 检查是否已经钓到足够数量的鱼鱼了
            if max_success_fishing_count != 0 and max_success_fishing_count <= self.success_fishing_count:
                logger.info(f"[任务结束] 已成功钓到了您所配置的{self.success_fishing_count}条鱼鱼，自动钓鱼结束！")
                return True
            
            self.fishing_count += 1
            # 打印当前钓鱼统计信息
            delta_time = now - self.fishing_start_time
            success_rate = (self.success_fishing_count / max(1, self.fishing_count - 1 - self.except_count) * 100) if self.fishing_count > 1 else 0.0
            exception_rate = (self.except_count / (self.fishing_count - 1) * 100) if self.fishing_count > 1 else 0.0
            avg_fish_per_rod = self.success_fishing_count / (self.used_rod_count + 1)
            print_center_block([
                f"累计进行 {self.fishing_count - 1} 次自动钓鱼 / 耗时 {format_seconds_to_hms(delta_time)}",
                f"成功钓上 {self.success_fishing_count} 只 => 神话{self.ssr_fish_count}只 / 珍稀{self.sr_fish_count}只 / 常见{self.r_fish_count}只",
                f"每条鱼鱼平均耗时 => {round(delta_time / max(1, self.success_fishing_count), 1)} 秒",
                f"消耗配件 => {self.used_rod_count}个鱼竿 / {self.used_bait_count}个鱼饵",
                f"钓鱼成功率 => {round(success_rate, 1)}% / 可恢复异常率：{round(exception_rate, 1)}%",
                f"每个鱼竿平均可钓 => {round(avg_fish_per_rod, 1)} 条鱼"
            ])
            
            # 1.1 直接点击一下指定位置 | 可以直接解决月卡和省电模式问题
            context.tasker.controller.post_click(640, 10).wait()
            time.sleep(1)

            # 2. 环境检查
            env_check_result = self.env_check(context, restart_for_except, max_restart_count)
            if env_check_result == -1:
                logger.error("[任务结束] 自动钓鱼环境检查出现无法重试错误，结束任务")
                return False
            elif env_check_result > 0:
                # 等待指定时间后继续下一次循环
                time.sleep(env_check_result)
                continue
            else:
                # 环境检查通过，等待1秒继续钓鱼流程
                time.sleep(1)

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
            logger.info("[任务准备] 开始抛竿，等待鱼鱼咬钩...")
            context.run_action("点击抛竿按钮")
            time.sleep(1)

            # 5. 检测鱼鱼是否咬钩 | 检测30秒，检测时间长，如果有中断命令就直接结束
            need_next = True  # 是否需要进行下一步 | 不需要就是被手动终止任务了
            wait_for_fish_times = 0
            while wait_for_fish_times < 300:
                if not self.check_running(context):
                    need_next = False
                    break
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                is_hooked: RecognitionDetail | None = context.run_recognition("检测鱼鱼是否咬钩", img)
                if is_hooked and is_hooked.hit:
                    del is_hooked, img
                    logger.info("[执行钓鱼] 鱼鱼咬钩了！")
                    break
                time.sleep(0.1)
                wait_for_fish_times += 1
            # 超时还没检测到鱼鱼咬钩 | 重新开始检测环境
            if wait_for_fish_times >= 300:
                logger.info("[执行钓鱼] 超过30秒未检测到鱼鱼咬钩，将重新开始环境检测")
                continue
            # 30秒检测内如果没有下一次了，说明钓鱼被强制结束了
            if not need_next:
                break

            # 6. 开始收线循环
            need_next = self.reel_loop(context)
            # 没有下一次了，说明钓鱼被强制结束了
            if not need_next:
                break
            time.sleep(3)

            # 7.1 本次钓鱼完成，再次检测并点击继续钓鱼按钮进行第二次钓鱼
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
            if is_continue_fishing and is_continue_fishing.hit:
                self.success_fishing_count += 1
                # 检查钓鱼结果
                self.check_fishing_result(context, img)
                time.sleep(1.5)
                # 点击继续钓鱼按钮
                context.run_action("点击继续钓鱼按钮")
            else:
                logger.info(f"[钓鱼结果] 鱼鱼跑掉了...")
            del is_continue_fishing, img
            time.sleep(1)

        logger.warning("[任务结束] 自动钓鱼已结束！")
        return True
    
    def env_check(
        self,
        context: Context,
        restart_for_except: bool = True,
        max_restart_count: int = 5
    ) -> int:
        """
        环境检查

        Args:
            context: 控制器上下文
            restart_for_except: 如遇到不可恢复异常，是否重启游戏，默认True重启
            max_restart_count: 最大重启游戏次数限制，默认5次

        Returns:
            等待下次钓鱼的时间（秒），0表示环境检查通过可以钓鱼，-1表示出现不可恢复错误需要结束任务
        """
        # 1. 检测进入钓鱼按钮
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        fishing_result: RecognitionDetail | None = context.run_recognition("检测进入钓鱼按钮", img)
        if fishing_result and fishing_result.hit:
            logger.info("[任务准备] 正在进入钓鱼台，等待5秒...")
            context.run_action("点击进入钓鱼按钮")
            # 走5秒，有些地方会卡住比较慢
            time.sleep(5)
            # 识别出了：走进钓鱼台，并重新截图
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        elif fishing_result:
            # 部分钓鱼地点背景影响严重，以防万一再次判断
            target_chars = {"钓", "鱼"}
            texts = {item.text for item in fishing_result.all_results}  # type: ignore
            if target_chars.issubset(texts):
                logger.info("[任务准备] 疑似钓鱼按钮，正在尝试进入钓鱼台，等待5秒...")
                context.run_action("点击进入钓鱼按钮")
                # 走5秒，有些地方会卡住比较慢
                time.sleep(5)
                # 疑似识别出了：走进钓鱼台，并重新截图
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            else:
                logger.info('[任务准备] 没有检测到钓鱼按钮，可能已经在钓鱼中，将直接检测抛竿按钮')
        else:
            logger.error('[任务结束] 识别节点不存在，逻辑不可达，请GitHub提交Issue反馈')
            return -1

        # 2. 检测抛竿按钮
        reeling_result: RecognitionDetail | None = context.run_recognition("检测抛竿按钮", img)
        if reeling_result and reeling_result.hit:
            logger.info("[任务准备] 检测到抛竿按钮，环境检查通过")
            del fishing_result, reeling_result, img
            return 0

        # 3. 检测继续钓鱼按钮
        logger.info('[任务准备] 没有检测到抛竿按钮，可能是在继续钓鱼界面')
        is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
        if is_continue_fishing and is_continue_fishing.hit:
            logger.info("[任务准备] 检测到继续钓鱼按钮，将点击按钮，环境检查通过")
            time.sleep(1.5)
            context.run_action("点击继续钓鱼按钮")
            del fishing_result, reeling_result, is_continue_fishing, img
            return 0
        
        logger.warning('[任务准备] 没有检测到继续钓鱼按钮，可能是遇到掉线/切线情况')
        self.except_count += 1  # type: ignore
        
        # 4. 检查其他意外情况
        disconnect_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "确认", "roi": [767, 517, 59, 27]}
            },
        )
        if disconnect_result and disconnect_result.hit:
            # 有确认按钮：很有可能是掉线了
            logger.info("[任务准备] 有确认按钮，可能是掉线重连按钮，正在点击重连，等待30秒后重试...")
            context.tasker.controller.post_click(797, 532).wait()
            time.sleep(2)

            # 检测是否有再次确认按钮
            disconnect_result: RecognitionDetail | None = context.run_recognition(
                "通用文字识别",
                img,
                pipeline_override={
                    "通用文字识别": {"expected": "确认", "roi": [614, 518, 50, 28]}
                },
            )
            if disconnect_result and disconnect_result.hit:
                # 大概率是服务器炸了，要回到主界面了
                logger.info("[任务准备] 检测到再次确认按钮，继续点击确认，等待30秒后重试...")
                context.tasker.controller.post_click(637, 529).wait()
        else:
            # 检测一下是否在登录页面
            logger.info("[任务准备] 检测不到确认按钮，可能是回到主界面...")
            login_result: RecognitionDetail | None = context.run_recognition("点击连接开始", img)
            if login_result and login_result.hit:
                logger.info("[任务准备] 检测到主界面连接开始按钮，准备登录游戏...")
                # 识别到开始界面
                context.tasker.controller.post_click(639, 602).wait()
                time.sleep(10)
                # 识别出了：进入选角色界面，并重新截图
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            del login_result

            # 检测一下是否在选择角色进入游戏页面
            entry_result: RecognitionDetail | None = context.run_recognition("点击进入游戏", img)
            if entry_result and entry_result.hit:
                # 识别到进入游戏
                logger.info("[任务准备] 登录结束，点击进入游戏，等待90秒...")
                context.tasker.controller.post_click(1103, 632).wait()
                del entry_result
                return 90
            del entry_result

            # 若开启不可恢复异常重启选项，则直接重启游戏
            if restart_for_except and self.restart_count < max_restart_count:  # type: ignore
                # 什么都检测不到，直接重启游戏得了
                logger.info("[任务准备] 检测不到进入游戏按钮，准备直接重启游戏，等待240秒...")
                restart_and_login_xhgm(context)
                self.restart_count += 1  # type: ignore
                return 0
            logger.info("[任务准备] 检测不到进入游戏按钮，等待30秒...")
        del disconnect_result, fishing_result, reeling_result, img
        # 等待30秒后直接进入下个循环
        return 30
    
    def ensure_equipment(
        self,
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

        Args:
            context: 控制器上下文
            type_str: 配件类型字符串（鱼竿 / 鱼饵）
            add_task: 检测是否需要添加配件任务名称
            add_action: 点击添加配件动作名称
            buy_task: 检测是否需要购买配件任务名称
            buy_actions: 购买配件动作名称列表
            use_action: 点击使用配件动作名称
            
        Returns:
            None
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
            if type_str == "鱼竿":
                self.used_rod_count += 1  # type: ignore
                logger.info(f"[任务准备] 当前将购买1个{type_str}")
            else:
                logger.info(f"[任务准备] 当前将购买200个{type_str}")
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
        1. 收线键的两种状态：
            - 初始模式 -> 一直按住收线键 | 目前可能出现按不住的情况，暂时换回初始节奏模式
            - 节奏模式 -> 循环进行：按住${press_duration_reel}秒后停${release_duration_reel}秒
        2. 初始状态 -> 收线键：初始模式；方向键：不动
        3. 识别到箭头：
            - 识别冷却期未到 -> 不改变之前两个按键的状态
            - 同向再次按压冷却期未到 & 同方向 -> 不改变之前两个按键的状态
            - 同向再次按压冷却期到了 & 同方向 -> 收线键：不改变之前的状态；方向键：再次朝对应方向按压${press_duration_bow}秒后松开
            - 不同方向 -> 收线键：保持节奏模式；方向键：换对应方向按压${press_duration_bow}秒后松开
            - 不同方向但前一次方向键未松开 -> 收线键：保持节奏模式；方向键：松开
        4. 张力上限检测：
            - 连续检测不通过 -> 不改变之前两个按键的状态
            - 连续检测通过 -> 收线键：立即停止按压${tension_press_duration}秒，停止按压期间不可被箭头变化打断，随后重置节奏模式重新开始；方向键：不改变之前的状态

        Args:
            context: 控制器上下文

        Returns:
            是否继续下一次钓鱼：True / False
        """

        # ========== 可配置参数 ==========
        max_reel_time = 120  # 最长收线时间，防止意外卡死
        press_duration_reel = 2.8  # 收线按压时长
        release_duration_reel = 0.2  # 收线松开时长 | 收线松开时长 >= 循环检测间隔
        press_duration_bow = 2.8  # 方向按压时长
        loop_interval = 0.1  # 循环检测间隔 | 太短影响性能，太长影响收线
        arrow_cooldown = 0.8  # 箭头方向冷却时间，冷却期内不再检测
        same_arrow_cooldown = 3.2 # 同向再次按压冷却期，冷却期内同向不再按压 | 同向再次按压冷却期 >= 箭头方向冷却时间
        tension_check_duration = 0.2  # 连续检测张力满的时间阈值
        tension_press_duration = 1.1  # 张力满暂停收线的时间

        # ========== 状态变量 ==========
        first_start_time = time.time()  # 循环开始时间
        is_first_cycle = True  # 是否是第一次循环
        is_reel_pressed = False  # 当前收线键状态
        cycle_start_time = None  # 收线键节奏循环开始时间
        last_arrow_detect_time = 0  # 上次确认箭头的时间戳
        last_arrow_direction = None  # 上次箭头方向
        is_bow_pressed = False  # 当前方向键状态
        bow_release_time = 0  # 当前方向松开的时间
        last_bow_press_time = 0  # 最近一次方向键实际按压的时间戳
        tension_peak_start_time = None  # 检测到张力已满的时间戳
        tension_pause_deadline = 0  # 张力上限打断截至时间

        while self.check_running(context):
            # 超过最长收线时间，强制结束本次钓鱼
            now = time.time()

            # ===== 最大收线时间保护 =====
            if now - first_start_time >= max_reel_time:
                logger.warning(f"[执行钓鱼] 收线时间超过{max_reel_time}秒，强制结束本次钓鱼")
                if is_reel_pressed:
                    self.stop_reel_in(context)
                if is_bow_pressed:
                    self.stop_bow(context)
                return True

            # ===== 获取截图 =====
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()

            # ===== 检查是否还在收线状态 =====
            if not self.check_if_reeling(context, img):
                self.used_bait_count += 1  # type: ignore
                logger.info("[执行钓鱼] 当前已不在收线状态，等待一会检测继续钓鱼按钮...")
                del img
                if is_reel_pressed:
                    self.stop_reel_in(context)
                if is_bow_pressed:
                    self.stop_bow(context)
                return True

            # ===== 张力检测 =====
            if tension_pause_deadline <= now:
                tension_hit: RecognitionDetail | None = context.run_recognition("检测张力是否到达上限", img)
                if tension_hit and tension_hit.hit:
                    if tension_peak_start_time is None:
                        # 第一次到张力上限时间点
                        tension_peak_start_time = now
                    elif now - tension_peak_start_time >= tension_check_duration:
                        # 到张力上限了
                        logger.info("[执行钓鱼] 张力到达上限 -> 收线键：强制暂停一会；方向键：不变化")
                        tension_pause_deadline = now + tension_press_duration
                        tension_peak_start_time = None
                        # 重置节奏循环
                        cycle_start_time = tension_pause_deadline
                else:
                    # 未到张力上限
                    tension_peak_start_time = None

            # ===== 箭头检测 =====
            confirmed_arrow = None
            if now - last_arrow_detect_time >= arrow_cooldown:
                confirmed_arrow = self.get_bow_direction(context, img)

            # 检测完就删除截图
            del img

            # ===== 根据箭头结果处理按键状态 =====
            if cycle_start_time is None and confirmed_arrow is None:
                # 初始无箭头 -> 收线键：进入初始模式；方向键：不动
                if not is_reel_pressed:
                    logger.info("[执行钓鱼] 初始无箭头 -> 收线键：进入初始模式；方向键：松开")
                    # 按住收线键 | 按两次防止出现异常
                    if self.start_reel_in(context):
                        if is_first_cycle:
                            is_first_cycle = False
                        else:
                            is_reel_pressed = True
                # 直接进入节奏模式 | 临时处理，防止按不住收线键的情况，后续不需要请注释下面一行
                cycle_start_time = now

            elif confirmed_arrow is not None and last_arrow_direction is None:
                # 首次确认箭头方向 -> 收线键：开始节奏模式；方向键：按住一会后松开
                logger.info(f"[执行钓鱼] 首次方向：{confirmed_arrow} -> 收线键：开始节奏模式；方向键：常规模式")
                # 时间变量赋值
                cycle_start_time = now
                last_arrow_direction = confirmed_arrow
                last_arrow_detect_time = now
                # 按住方向键
                if self.start_bow(context, confirmed_arrow):
                    is_bow_pressed = True
                    bow_release_time = now + press_duration_bow
                    last_bow_press_time = now

            elif confirmed_arrow is not None and confirmed_arrow != last_arrow_direction:
                # 时间变量赋值
                cycle_start_time = now + release_duration_reel
                last_arrow_direction = confirmed_arrow
                last_arrow_detect_time = now
                if is_bow_pressed:
                    # 不同方向但前一次方向键未松开 -> 收线键：保持节奏模式；方向键：松开
                    logger.info(f"[执行钓鱼] 方向变化(快) -> 收线键：保持节奏模式；方向键：松开")
                    bow_release_time = now
                else:
                    # 不同方向 -> 收线键：保持节奏模式；方向键：按住一会后松开
                    logger.info(f"[执行钓鱼] 方向变化：{confirmed_arrow} -> 收线键：保持节奏模式；方向键：常规模式")
                    # 按住方向键
                    if self.start_bow(context, confirmed_arrow):
                        is_bow_pressed = True
                        bow_release_time = now + press_duration_bow
                        last_bow_press_time = now

            elif confirmed_arrow is not None and confirmed_arrow == last_arrow_direction:
                # 相同方向 -> 根据同向冷却状态分别处理
                if now - last_bow_press_time < same_arrow_cooldown:
                    # 同向再次按压冷却期未到 -> 不改变之前两个按键的状态
                    pass
                else:
                    # 同向再次按压冷却期到了 -> 收线键：不改变之前的状态；方向键：再次按住一会后松开
                    logger.info(f"[执行钓鱼] 方向未变 -> 收线键：不变化；方向键：重启常规模式")
                    last_arrow_detect_time = now
                    if self.start_bow(context, confirmed_arrow):
                        is_bow_pressed = True
                        bow_release_time = now + press_duration_bow
                        last_bow_press_time = now

            # ===== 节奏模式中统一控制收线逻辑 =====
            if cycle_start_time is not None:
                if now < tension_pause_deadline:
                    # 张力上限暂停期间强制松开
                    if is_reel_pressed and self.stop_reel_in(context):
                        is_reel_pressed = False
                else:
                    # 正常节奏模式中根据时间判断是否收线
                    elapsed = (now - cycle_start_time) % (press_duration_reel + release_duration_reel)
                    if elapsed < press_duration_reel:
                        # 需要按压
                        if not is_reel_pressed and self.start_reel_in(context):
                            is_reel_pressed = True
                    else:
                        # 需要松开
                        if is_reel_pressed and self.stop_reel_in(context):
                            is_reel_pressed = False

            # ===== 方向键松开控制 =====
            if is_bow_pressed and now >= bow_release_time:
                self.stop_bow(context)
                is_bow_pressed = False

            # ===== 控制循环频率 =====
            time.sleep(loop_interval)

        return False

    @staticmethod
    def check_if_reeling(context: Context, img: numpy.ndarray) -> bool:
        """
        检查当前是否在收线：
        1. 钓到鱼鱼了：检测继续钓鱼按钮
        2. 鱼鱼跑路了：检测是否在抛竿界面

        Args:
            context: 控制器上下文
            img: 当前截图

        Returns:
            是否在收线中：True / False
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
        获取箭头方向（'左' / '右' / None）带分数阈值：
        1. 左右箭头分数低于 score_threshold 视为无效
        2. 分数差小于 min_score_diff，则视为无效（避免接近分数误判）
        3. 返回方向字符串或 None

        Args:
            context: 控制器上下文
            img: 当前截图
            score_threshold: 分数阈值
            min_score_diff: 分数差阈值

        Returns:
            箭头方向字符串或 None
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
            bow_direction = "左"
        elif bow_right_score >= score_threshold and bow_right_score > bow_left_score:
            bow_direction = "右"
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
        if direction == "左":
            x = 150
        elif direction == "右":
            x = 320
        else:
            return False
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

    def check_fishing_result(self, context: Context, img: numpy.ndarray) -> None:
        """
        检查该次成功的钓鱼结果

        Args:
            context: 控制器上下文
            img: 钓鱼结果截图
        
        Returns:
            None
        """
        # 稀有度
        rarity_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "[\\S\\s]*", "roi": [734, 531, 91, 23]}
            }
        )
        rare = "未知"
        if rarity_result and rarity_result.hit:
            fish_rarity = rarity_result.best_result.text  # type: ignore
            rare = get_best_match_single(fish_rarity, self.FISH_RARITY_LIST)
            # 计数
            if rare == "神话":
                self.ssr_fish_count += 1  # type: ignore
            elif rare == "珍稀":
                self.sr_fish_count += 1  # type: ignore
            elif rare == "常见":
                self.r_fish_count += 1  # type: ignore
        del rarity_result

        # 鱼名
        fish_name_result: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": "[\\S\\s]*", "roi": [711, 488, 264, 36]}
            }
        )
        fish = "未知"
        if fish_name_result and fish_name_result.hit:
            fish_name = fish_name_result.best_result.text  # type: ignore
            fish = get_best_match_single(fish_name, self.FISH_NAME_LIST)
        del fish_name_result

        logger.info(f"[钓鱼结果] 钓上了 [{fish}] 稀有度：[{rare}]")
