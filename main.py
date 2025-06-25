"""
Yandere Github Stalker Plugin
"""
import asyncio
import json
import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.star.filter.permission import PermissionType

from .src.github_api import GitHubAPI
from .src.notification_renderer import NotificationRenderer
from .src.pushed_event_id_manager import PushedEventIdManager
from .src.event_processor import EventProcessor
from .src.notification_sender import NotificationSender
from .src.config_manager import ConfigManager

@register("astrbot_plugin_yandere_github_stalker", "SXP-Simon", "Yandere Github Stalker Plugin", "1.0.0")
class YandereGithubStalker(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        """初始化插件"""
        super().__init__(context)
        
        # 初始化组件
        self.config_manager = ConfigManager(config)
        self.github_api = GitHubAPI(self.config_manager)
        
        # 初始化事件ID管理器
        os.makedirs("data", exist_ok=True)
        self.pushed_event_ids_path = os.path.join("data", "github_pushed_event_ids.json")
        self.pushed_event_ids_manager = PushedEventIdManager(self.pushed_event_ids_path)
        
        # 初始化其他组件
        self.event_processor = EventProcessor(
            event_limit=self.config_manager.get_event_limit(),
            pushed_event_ids_manager=self.pushed_event_ids_manager,
            config_manager=self.config_manager
        )
        self.notification_renderer = NotificationRenderer(self.config_manager)
        self.notification_sender = NotificationSender(
            notification_renderer=self.notification_renderer,
            context=self.context,
            html_render=self.html_render
        )
        
        # 初始化状态
        self.is_monitoring = False
        self.monitoring_task = None
        
        # 启动监控任务
        asyncio.create_task(self.start_monitoring())
        logger.debug(f"Yandere Github Stalker: 插件初始化完成，事件限制：{self.config_manager.get_event_limit()}")

    def _prepare_command(self, event: AstrMessageEvent):
        """准备命令执行环境"""
        event.stop_event()
        event.should_call_llm(False)

    @filter.command_group("yandere")
    def yandere_group(self):
        """Yandere Github Stalker 命令组"""
        pass

    @yandere_group.command("test")
    async def test_notification(self, event: AstrMessageEvent):
        """测试GitHub活动通知图片生成"""
        try:
            self._prepare_command(event)
            
            test_data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
            if not os.path.exists(test_data_path):
                return event.plain_result("❌ 测试数据文件不存在").stop_event()

            with open(test_data_path, "r", encoding="utf-8") as f:
                test_events = json.load(f)

            test_events = sorted(test_events, key=lambda x: x.get("created_at", ""), reverse=True)[:3]
            username = test_events[0].get("actor", {}).get("login", "test") if test_events else "test"

            if self.config_manager.is_image_notification_enabled():
                for test_event in test_events:
                    success = await self.notification_sender.send_image_notification(
                        username,
                        test_event,
                        [event.unified_msg_origin]
                    )
                    if not success:
                        return event.plain_result("❌ 图片生成失败").stop_event()
            else:
                for test_event in test_events:
                    success = await self.notification_sender.send_text_notification(
                        username,
                        test_event,
                        [event.unified_msg_origin]
                    )
                    if not success:
                        return event.plain_result("❌ 文本通知发送失败").stop_event()

            return event.plain_result("✅ 测试完成").stop_event()
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 测试通知失败: {e}")
            return event.plain_result(f"❌ 测试失败: {e}").stop_event()

    @yandere_group.command("status")
    async def github_status(self, event: AstrMessageEvent):
        """显示当前视奸状态"""
        self._prepare_command(event)

        monitored_users = self.config_manager.get_monitored_users()
        target_sessions = self.config_manager.get_target_sessions()
        check_interval = self.config_manager.get_check_interval()
        pushed_count = len(self.pushed_event_ids_manager)
        
        msg = (
            f"Yandere Github Stalker 插件状态 ♥\n"
            f"视奸的用户们: {len(monitored_users)}位大可爱\n"
            f"推送目标: {len(target_sessions)}个频道\n"
            f"检查间隔: {check_interval}秒\n"
            f"已经记录了{pushed_count}条动态呢...诶嘿嘿 ♥"
        )
        return event.plain_result(msg).stop_event()

    @yandere_group.command("add")
    async def add_user(self, event: AstrMessageEvent, username: str):
        """添加一个GitHub用户到视奸列表"""
        self._prepare_command(event)

        try:
            monitored_users = self.config_manager.get_monitored_users()
            if username in monitored_users:
                return event.plain_result(f"❌ 用户 {username} 已经在视奸列表中了哦~").stop_event()
            
            # 验证用户是否存在
            events = await self.github_api.get_user_events(username)
            if not events:
                return event.plain_result(f"❌ 无法获取用户 {username} 的动态，请检查用户名是否正确").stop_event()

            monitored_users.append(username)
            self.config_manager.update_config("monitored_users", monitored_users)
            return event.plain_result(f"✅ 已将用户 {username} 加入视奸列表~").stop_event()
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 添加用户失败: {e}")
            return event.plain_result(f"❌ 添加用户失败: {e}").stop_event()

    @yandere_group.command("remove")
    async def remove_user(self, event: AstrMessageEvent, username: str):
        """从视奸列表中移除一个GitHub用户"""
        self._prepare_command(event)

        try:
            monitored_users = self.config_manager.get_monitored_users()
            if username not in monitored_users:
                return event.plain_result(f"❌ 用户 {username} 不在视奸列表中哦~").stop_event()
            
            monitored_users.remove(username)
            self.config_manager.update_config("monitored_users", monitored_users)
            return event.plain_result(f"✅ 已将用户 {username} 从视奸列表中移除~").stop_event()
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 移除用户失败: {e}")
            return event.plain_result(f"❌ 移除用户失败: {e}").stop_event()

    @yandere_group.command("enable")
    @filter.permission_type(PermissionType.ADMIN)
    async def enable_session(self, event: AstrMessageEvent):
        """启用当前会话的通知"""
        self._prepare_command(event)

        try:
            target_sessions = self.config_manager.get_target_sessions()
            session_id = event.unified_msg_origin
            
            if session_id in target_sessions:
                return event.plain_result("当前会话已启用通知").stop_event()
            
            target_sessions.append(session_id)
            self.config_manager.update_config("target_sessions", target_sessions)
            return event.plain_result("已启用当前会话的通知").stop_event()
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 启用会话失败: {e}")
            return event.plain_result(f"启用失败: {e}").stop_event()

    @yandere_group.command("disable")
    @filter.permission_type(PermissionType.ADMIN)
    async def disable_session(self, event: AstrMessageEvent):
        """禁用当前会话的通知"""
        self._prepare_command(event)

        try:
            target_sessions = self.config_manager.get_target_sessions()
            session_id = event.unified_msg_origin
            
            if session_id not in target_sessions:
                return event.plain_result("当前会话未启用通知").stop_event()
            
            target_sessions.remove(session_id)
            self.config_manager.update_config("target_sessions", target_sessions)
            return event.plain_result("已禁用当前会话的通知").stop_event()
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 禁用会话失败: {e}")
            return event.plain_result(f"禁用失败: {e}").stop_event()

    async def start_monitoring(self):
        """启动监控任务"""
        if self.is_monitoring:
            logger.warning("Yandere Github Stalker: 监控任务已在运行中")
            return

        if self.monitoring_task and not self.monitoring_task.done():
            logger.warning("Yandere Github Stalker: 监控任务已存在且未完成")
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Yandere Github Stalker: 监控任务已启动")

    async def stop_monitoring(self):
        """停止监控任务"""
        if not self.is_monitoring:
            logger.warning("Yandere Github Stalker: 监控任务未在运行")
            return

        self.is_monitoring = False
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Yandere Github Stalker: 监控任务已停止")

    async def _monitoring_loop(self):
        """监控循环"""
        try:
            while self.is_monitoring:
                try:
                    # 获取监控用户列表和目标会话列表
                    monitored_users = self.config_manager.get_monitored_users()
                    target_sessions = self.config_manager.get_target_sessions()

                    if not monitored_users:
                        logger.warning("Yandere Github Stalker: 没有配置监控用户")
                        await asyncio.sleep(60)  # 等待一分钟后重试
                        continue

                    if not target_sessions:
                        logger.warning("Yandere Github Stalker: 没有配置目标会话")
                        await asyncio.sleep(60)  # 等待一分钟后重试
                        continue

                    logger.debug(f"Yandere Github Stalker: 开始检查活动，监控用户：{monitored_users}，目标会话：{target_sessions}")

                    # 检查每个用户的活动
                    for username in monitored_users:
                        try:
                            # 获取用户活动
                            events = await self.github_api.get_user_events(username)
                            if not events:
                                logger.debug(f"Yandere Github Stalker: 用户 {username} 没有新活动")
                                continue

                            # 处理事件
                            new_events = await self.event_processor.process_events(events)
                            if not new_events:
                                logger.debug(f"Yandere Github Stalker: 用户 {username} 没有需要推送的新事件")
                                continue

                            logger.debug(f"Yandere Github Stalker: 用户 {username} 有 {len(new_events)} 条新事件需要推送")
                            logger.debug(f"Yandere Github Stalker: 待推送事件类型：{[e.get('type') for e in new_events]}")

                            # 发送通知
                            for idx, event in enumerate(new_events, 1):
                                event_id = event.get("id")
                                event_type = event.get("type")
                                logger.debug(f"Yandere Github Stalker: 准备推送第 {idx}/{len(new_events)} 个事件 {event_id}，类型：{event_type}")
                                
                                try:
                                    if self.config_manager.is_image_notification_enabled():
                                        logger.debug(f"Yandere Github Stalker: 尝试发送图片通知，事件ID：{event_id}")
                                        success = await self.notification_sender.send_image_notification(
                                            username, event, target_sessions
                                        )
                                    else:
                                        logger.debug(f"Yandere Github Stalker: 尝试发送文本通知，事件ID：{event_id}")
                                        success = await self.notification_sender.send_text_notification(
                                            username, event, target_sessions
                                        )

                                    if success:
                                        # 成功发送通知，标记为已推送
                                        await self.event_processor.mark_event_as_pushed(event_id)
                                        logger.debug(f"Yandere Github Stalker: 事件 {event_id} 推送成功并已标记为已推送")
                                    else:
                                        # 如果是因为模板缺失导致的失败，标记为已忽略
                                        if "模板缺失" in str(success):
                                            await self.event_processor.mark_event_as_ignored(event_id)
                                            logger.warning(f"Yandere Github Stalker: 事件 {event_id} 的模板缺失，已忽略")
                                        else:
                                            # 其他错误，记录错误但继续处理其他事件
                                            logger.warning(f"Yandere Github Stalker: 事件 {event_id} 推送失败，将在下次检查时重试")

                                except Exception as e:
                                    if "模板缺失" in str(e):
                                        # 如果是模板缺失错误，标记该事件为已忽略并继续处理其他事件
                                        await self.event_processor.mark_event_as_ignored(event_id)
                                        logger.warning(f"Yandere Github Stalker: 事件 {event_id} 的模板缺失，已忽略")
                                    else:
                                        # 其他错误，记录错误但继续处理其他事件
                                        logger.error(f"Yandere Github Stalker: 发送通知失败: {e}")
                                        logger.warning(f"Yandere Github Stalker: 事件 {event_id} 推送失败，将在下次检查时重试")

                                # 添加延迟以避免发送过快
                                await asyncio.sleep(1)

                            logger.debug(f"Yandere Github Stalker: 用户 {username} 的所有事件处理完成")

                        except Exception as e:
                            logger.error(f"Yandere Github Stalker: 处理用户 {username} 的活动时出错: {e}")
                            continue  # 继续处理下一个用户

                    # 等待下一次检查
                    check_interval = self.config_manager.get_check_interval()
                    logger.debug(f"Yandere Github Stalker: 等待 {check_interval} 秒后进行下一次检查")
                    await asyncio.sleep(check_interval)

                except Exception as e:
                    logger.error(f"Yandere Github Stalker: 检查活动失败: {e}")
                    await asyncio.sleep(60)  # 出错后等待一分钟再重试

        except asyncio.CancelledError:
            logger.info("Yandere Github Stalker: 监控任务被取消")
            raise
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 监控循环出现异常: {e}")
        finally:
            self.is_monitoring = False

    async def terminate(self):
        """插件卸载时调用"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        logger.info("Yandere Github Stalker: 插件已停止...有缘再见呢 ♥")