"""
GitHub User Activity Monitor Plugin
"""
import asyncio
import json
import time
import os
from typing import Dict, Optional, List
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp

from .src.github_api import GitHubAPI
from .src.notification_renderer import NotificationRenderer
from .src.message_sender import MessageSender

@register("astrbot_plugin_yandere_github_stalker", "Simon", "GitHub用户活动监控插件", "1.0.0")
class GitHubActivityMonitor(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.monitoring_task = None
        self.is_monitoring = False

        # 初始化组件
        self.github_api = GitHubAPI(config.get("github_token", ""))
        self.notification_renderer = NotificationRenderer()
        self.message_sender = MessageSender(context)

        # 创建数据目录
        os.makedirs("data", exist_ok=True)
        self.pushed_event_ids_path = os.path.join("data", "github_pushed_event_ids.json")
        self.pushed_event_ids = self._load_pushed_event_ids()

        # 启动监控任务
        asyncio.create_task(self.start_monitoring())

    def _load_pushed_event_ids(self):
        if os.path.exists(self.pushed_event_ids_path):
            try:
                with open(self.pushed_event_ids_path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_pushed_event_ids(self):
        try:
            with open(self.pushed_event_ids_path, "w", encoding="utf-8") as f:
                json.dump(list(self.pushed_event_ids), f)
        except Exception as e:
            logger.error(f"GitHub活动监控: 保存事件ID失败: {e}")

    async def start_monitoring(self):
        """启动监控任务"""
        try:
            # 等待一段时间再开始监控，确保插件完全加载
            await asyncio.sleep(10)
            logger.info("GitHub活动监控: 开始监控任务")

            # 启动时推送监控通知
            monitored_users = self.config.get("monitored_users", [])
            target_sessions = self.config.get("target_sessions", [])
            check_interval = self.config.get("check_interval", 300)
            await self.message_sender.send_startup_notification(monitored_users, target_sessions, check_interval)

            # 首次运行时初始化数据
            await self.check_activities()

            while True:
                try:
                    check_interval = self.config.get("check_interval", 300)  # 默认5分钟
                    await self.check_activities()
                    await asyncio.sleep(check_interval)
                except Exception as e:
                    logger.error(f"GitHub活动监控: 监控任务出错: {e}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再重试
        except Exception as e:
            logger.error(f"GitHub活动监控: 启动监控任务失败: {e}")

    async def check_user_activity(self, username: str, events: list, target_sessions: list):
        """
        检查单个用户的活动，并推送需要的消息
        :param username: GitHub用户名
        :param events: 事件列表（如test_data.json结构）
        :param target_sessions: 推送目标会话
        """
        new_events = [e for e in events if e.get("id") not in self.pushed_event_ids]
        if not new_events:
            return
        for activity in new_events:
            event_type = activity.get("type", "").lower().replace("event", "")
            config_key = f"monitor_{event_type}"
            if self.config.get(config_key, True):
                if self.config.get("enable_image_notification", True):
                    image_path = await self.notification_renderer.render_event_notification(activity)
                    if image_path:
                        await self.message_sender.send_image_notification(target_sessions, image_path)
                    else:
                        await self.message_sender.send_notification(target_sessions, activity)
                else:
                    await self.message_sender.send_notification(target_sessions, activity)
            # 记录已推送事件ID
            self.pushed_event_ids.add(activity.get("id"))
        self._save_pushed_event_ids()

    async def check_activities(self):
        """检查GitHub活动"""
        if self.is_monitoring:
            logger.debug("GitHub活动监控: 上一次检查还在进行中，跳过本次检查")
            return

        self.is_monitoring = True
        try:
            monitored_users = self.config.get("monitored_users", [])
            target_sessions = self.config.get("target_sessions", [])

            if not monitored_users:
                logger.debug("GitHub活动监控: 没有配置要监控的用户")
                return

            if not target_sessions:
                logger.debug("GitHub活动监控: 没有配置目标会话")
                return

            for username in monitored_users:
                try:
                    # 获取用户最新活动
                    activities = await self.github_api.get_user_events(username)
                    if activities:
                        # 调用新方法处理
                        await self.check_user_activity(username, activities, target_sessions)
                except Exception as e:
                    logger.error(f"GitHub活动监控: 检查用户 {username} 活动时出错: {e}")
        finally:
            self.is_monitoring = False

    @filter.command("github_test")
    async def test_notification(self, event: AstrMessageEvent):
        """测试GitHub活动通知图片生成"""
        try:
            # 读取测试数据
            test_data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
            if not os.path.exists(test_data_path):
                yield event.plain_result("❌ 测试数据文件不存在")
                return

            with open(test_data_path, "r", encoding="utf-8") as f:
                test_events = json.load(f)
            # 只推送未推送过的测试事件
            new_events = [e for e in test_events if e.get("id") not in self.pushed_event_ids]
            for test_event in new_events:
                event_type = test_event["type"]
                image_path = await self.notification_renderer.render_event_notification(test_event)
                if image_path:
                    await self.message_sender.send_image_notification(
                        [event.session_id],  # 只发送给触发命令的会话
                        image_path
                    )
                    await asyncio.sleep(1)
                else:
                    await self.message_sender.send_notification([event.session_id], test_event)
                self.pushed_event_ids.add(test_event.get("id"))
            self._save_pushed_event_ids()
            yield event.plain_result("✅ 测试通知已发送")
        except Exception as e:
            logger.error(f"GitHub活动监控: 生成测试通知失败: {e}")
            yield event.plain_result(f"❌ 生成测试通知失败: {e}")

    @filter.command("github_status")
    async def github_status(self, event: AstrMessageEvent):
        """显示当前监控状态"""
        monitored_users = self.config.get("monitored_users", [])
        target_sessions = self.config.get("target_sessions", [])
        check_interval = self.config.get("check_interval", 300)
        pushed_count = len(self.pushed_event_ids)
        msg = (
            f"GitHub活动监控插件状态：\n"
            f"监控用户数: {len(monitored_users)}\n"
            f"推送目标会话数: {len(target_sessions)}\n"
            f"检查间隔: {check_interval} 秒\n"
            f"已推送事件数: {pushed_count}"
        )
        yield event.plain_result(msg)

    async def terminate(self):
        """插件卸载时调用"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("GitHub活动监控: 插件已停止")
