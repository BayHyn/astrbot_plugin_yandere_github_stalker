"""
Yandere Github Stalker Plugin
"""
import asyncio
import json
import os
import base64
from datetime import datetime
import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.message.components import Image, Plain
from astrbot.core.platform.message_type import MessageType
from astrbot.core.star.config import put_config, update_config

from .src.github_api import GitHubAPI
from .src.notification_renderer import NotificationRenderer
from .src.yandere_templates import YandereTemplates


@register("astrbot_plugin_yandere_github_stalker", "SXP-Simon", "Yandere Github Stalker Plugin", "1.0.0")
class YandereGithubStalker(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.github_api = GitHubAPI()
        self.notification_renderer = NotificationRenderer()
        self.config = None
        
        # 初始化配置
        put_config(
            "astrbot_plugin_yandere_github_stalker",
            "目标会话",
            "target_sessions",
            [],
            "接收通知的会话列表"
        )
        put_config(
            "astrbot_plugin_yandere_github_stalker",
            "监控用户",
            "stalking_users",
            [],
            "要监控的GitHub用户列表"
        )

    async def initialize(self) -> None:
        """初始化插件，启动定时任务"""
        logger.info("Yandere Github Stalker: 病娇版监控启动...")
        # 获取配置实例
        self.config = self.context.get_config()
        asyncio.create_task(self._check_updates())

    async def _check_updates(self):
        """定期检查GitHub动态"""
        while True:
            try:
                target_sessions = self._get_config("target_sessions")
                stalking_users = self._get_config("stalking_users")
                
                if not target_sessions:
                    logger.debug("Yandere Github Stalker: 没有配置目标会话")
                elif not stalking_users:
                    logger.debug("Yandere Github Stalker: 没有配置监控用户")
                else:
                    for user in stalking_users:
                        activities = await self.github_api.get_user_events(user)
                        if activities:
                            await self.check_user_activity(user, activities, target_sessions)
                
                await asyncio.sleep(300)  # 每5分钟检查一次
            except Exception as e:
                logger.error(f"Yandere Github Stalker: 检查更新失败: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试

    def _get_config(self, key: str):
        """获取配置值"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "astrbot_plugin_yandere_github_stalker.json"
            )
            with open(config_path, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
                return config.get(key, {}).get("value", [])
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 读取配置失败: {e}")
            return []

    @filter.command("yandere test")
    async def test_notification(self, event: AstrMessageEvent):
        """测试通知功能"""
        try:
            # 获取一个示例用户的活动
            test_user = "torvalds"  # 使用Linus作为测试用户
            activities = await self.github_api.get_user_events(test_user)
            
            if activities:
                # 只处理最新的一条动态作为测试
                await self.check_user_activity(test_user, [activities[0]], [event.unified_msg_origin])
                await event.send(MessageChain([Plain("测试通知已发送")]))
            else:
                await event.send(MessageChain([Plain("获取测试数据失败")]))
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 测试通知失败: {e}")
            await event.send(MessageChain([Plain(f"测试失败: {e}")]))
        return True

    @filter.command("yandere status")
    async def show_status(self, event: AstrMessageEvent):
        """显示当前监控状态"""
        target_sessions = self._get_config("target_sessions")
        stalking_users = self._get_config("stalking_users")
        
        status = []
        status.append("当前监控状态:")
        status.append(f"- 监控用户数: {len(stalking_users)}")
        if stalking_users:
            status.append("- 监控用户列表:")
            for user in stalking_users:
                status.append(f"  * {user}")
        
        status.append(f"- 通知会话数: {len(target_sessions)}")
        if target_sessions:
            status.append("- 通知会话列表:")
            for session in target_sessions:
                status.append(f"  * {session}")
        
        await event.send(MessageChain([Plain("\n".join(status))]))
        return True

    # @filter.command("yandere add {username}")
    # async def add_user(self, event: AstrMessageEvent, username: str):
    #     """添加监控用户"""
    #     try:
    #         # 验证用户是否存在
    #         if not await self.github_api.check_user_exists(username):
    #             await event.send(MessageChain([Plain(f"GitHub用户 {username} 不存在")]))
    #             return True
            
    #         stalking_users = self._get_config("stalking_users")
    #         if username in stalking_users:
    #             await event.send(MessageChain([Plain(f"用户 {username} 已在监控列表中")]))
    #             return True
            
    #         stalking_users.append(username)
    #         update_config("astrbot_plugin_yandere_github_stalker", "stalking_users", stalking_users)
    #         await event.send(MessageChain([Plain(f"已添加用户 {username} 到监控列表")]))
    #         return True
    #     except Exception as e:
    #         logger.error(f"Yandere Github Stalker: 添加用户失败: {e}")
    #         await event.send(MessageChain([Plain(f"添加用户失败: {e}")]))
    #         return True

    # @filter.command("yandere remove {username}")
    # async def remove_user(self, event: AstrMessageEvent, username: str):
    #     """移除监控用户"""
    #     try:
    #         stalking_users = self._get_config("stalking_users")
    #         if username not in stalking_users:
    #             await event.send(MessageChain([Plain(f"用户 {username} 不在监控列表中")]))
    #             return True
            
    #         stalking_users.remove(username)
    #         update_config("astrbot_plugin_yandere_github_stalker", "stalking_users", stalking_users)
    #         await event.send(MessageChain([Plain(f"已从监控列表中移除用户 {username}")]))
    #         return True
    #     except Exception as e:
    #         logger.error(f"Yandere Github Stalker: 移除用户失败: {e}")
    #         await event.send(MessageChain([Plain(f"移除用户失败: {e}")]))
    #         return True

    @filter.command("yandere enable")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def enable_session(self, event: AstrMessageEvent):
        """启用当前会话的通知"""
        try:
            target_sessions = self._get_config("target_sessions")
            session_id = event.unified_msg_origin
            
            if session_id in target_sessions:
                await event.send(MessageChain([Plain("当前会话已启用通知")]))
                return True
            
            target_sessions.append(session_id)
            update_config("astrbot_plugin_yandere_github_stalker", "target_sessions", target_sessions)
            await event.send(MessageChain([Plain("已启用当前会话的通知")]))
            return True
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 启用会话失败: {e}")
            await event.send(MessageChain([Plain(f"启用失败: {e}")]))
            return True

    @filter.command("yandere disable")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def disable_session(self, event: AstrMessageEvent):
        """禁用当前会话的通知"""
        try:
            target_sessions = self._get_config("target_sessions")
            session_id = event.unified_msg_origin
            
            if session_id not in target_sessions:
                await event.send(MessageChain([Plain("当前会话未启用通知")]))
                return True
            
            target_sessions.remove(session_id)
            update_config("astrbot_plugin_yandere_github_stalker", "target_sessions", target_sessions)
            await event.send(MessageChain([Plain("已禁用当前会话的通知")]))
            return True
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 禁用会话失败: {e}")
            await event.send(MessageChain([Plain(f"禁用失败: {e}")]))
            return True

    async def check_user_activity(self, username: str, activities: list, target_sessions: list):
        """检查用户活动并发送通知"""
        try:
            for activity in activities:
                message = await self.notification_renderer.render_notification(username, activity)
                if message:
                    for session in target_sessions:
                        try:
                            await self.context.platform_manager.send_message(
                                session,
                                MessageChain([Plain(message)])
                            )
                        except Exception as e:
                            logger.error(f"Yandere Github Stalker: 发送通知到会话 {session} 失败: {e}")
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 处理用户 {username} 活动失败: {e}")
