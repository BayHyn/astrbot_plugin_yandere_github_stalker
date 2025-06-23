"""
GitHub User Activity Monitor Plugin
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


from .src.github_api import GitHubAPI
from .src.notification_renderer import NotificationRenderer
from .src.yandere_templates import YandereTemplates


@register("astrbot_plugin_yandere_github_stalker", "Simon", "GitHub用户活动监控插件 - 病娇版", "1.0.0")
class GitHubActivityMonitor(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.monitoring_task = None
        self.is_monitoring = False

        # 初始化组件
        self.github_api = GitHubAPI(config.get("github_token", ""))
        
        # 获取自定义模板
        custom_templates = {}
        for key, value in config.items():
            if key.startswith('monitor_') and isinstance(value, dict):
                event_type = self._convert_monitor_to_event_type(key)
                if 'enabled' in value and value['enabled']:
                    custom_templates[event_type] = {k: v for k, v in value.items() if k != 'enabled'}

        self.notification_renderer = NotificationRenderer(custom_templates)

        # 创建数据目录
        os.makedirs("data", exist_ok=True)
        self.pushed_event_ids_path = os.path.join(
            "data", "github_pushed_event_ids.json")
        self.pushed_event_ids = self._load_pushed_event_ids()

        # 启动监控任务
        asyncio.create_task(self.start_monitoring())

    def _convert_monitor_to_event_type(self, monitor_key: str) -> str:
        """
        将monitor_配置键转换为事件类型
        例如: monitor_push -> PushEvent
        """
        # 移除 "monitor_" 前缀
        event_type = monitor_key[8:]
        
        # 特殊情况处理
        event_type_mapping = {
            'push': 'PushEvent',
            'issues': 'IssuesEvent',
            'pull_request': 'PullRequestEvent',
            'star': 'WatchEvent',  # GitHub API 中 Star 事件实际上是 WatchEvent
            'fork': 'ForkEvent',
            'create': 'CreateEvent',
            'delete': 'DeleteEvent',
            'public': 'PublicEvent',
            'member': 'MemberEvent',
            'commit_comment': 'CommitCommentEvent'
        }
        
        return event_type_mapping.get(event_type, event_type.capitalize() + 'Event')

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
            logger.info("GitHub活动监控: 病娇版监控启动...")
            if not self.config.get("github_token"):
                logger.warning("GitHub活动监控: 未配置GitHub Token，可能会受到API访问限制")

            while True:
                try:
                    check_interval = self.config.get(
                        "check_interval", 300)  # 默认5分钟
                    await self.check_activities()
                    await asyncio.sleep(check_interval)
                except Exception as e:
                    logger.error(f"GitHub活动监控: 监控任务出错: {e}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再重试
        except Exception as e:
            logger.error(f"GitHub活动监控: 启动监控任务失败: {e}")

    def _validate_session(self, session: str) -> bool:
        """
        验证会话ID格式是否正确
        :param session: 会话ID字符串
        :return: 是否合法
        """
        try:
            parts = session.split(":")
            if len(parts) != 3:
                logger.warning(f"GitHub活动监控: 不合法的会话ID格式: {session}，应为 '平台:ID:类型'")
                return False
            platform, id_, type_ = parts
            return True
        except Exception as e:
            logger.warning(f"GitHub活动监控: 会话ID格式验证失败: {session}, 错误: {e}")
            return False

    async def check_user_activity(self, username: str, events: list, target_sessions: list):
        """
        检查单个用户的活动，并推送需要的消息
        :param username: GitHub用户名
        :param events: 事件列表
        :param target_sessions: 推送目标会话
        """
        new_events = [e for e in events if e.get("id") not in self.pushed_event_ids]
        if not new_events:
            return

        # 只处理最新的5条动态
        new_events = sorted(new_events, key=lambda x: x.get("created_at", ""), reverse=True)[:5]

        try:
            # 获取用户头像
            avatar_url = new_events[0].get('actor', {}).get('avatar_url', '')
            avatar_base64 = ""
            if avatar_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            avatar_data = await response.read()
                            avatar_base64 = f"data:image/png;base64,{base64.b64encode(avatar_data).decode('utf-8')}"

            # 准备消息内容
            message_chain = None
            image_path = None

            # 如果启用了图片通知，尝试生成图片
            if self.config.get("enable_image_notification", True):
                # 使用Jinja2渲染HTML
                html_content = self.notification_renderer.render_html(
                    username=username,
                    avatar_base64=avatar_base64,
                    events=new_events
                )

                # 使用html_render渲染模板
                image_path = await self.html_render(
                    tmpl=html_content,
                    data={
                        "username": username,
                        "avatar_base64": avatar_base64,
                        "events": new_events
                    },
                    return_url=False  # 返回文件路径而不是URL
                )
                if image_path:
                    img = Image.fromFileSystem(image_path)
                    if img:
                        message_chain = MessageChain([img])

            # 如果没有成功生成图片消息，使用文本消息
            if not message_chain:
                text = self.notification_renderer.create_text_notification(username, new_events)
                message_chain = MessageChain([Plain(text)])

            # 发送消息到所有目标会话
            for session in target_sessions:
                try:
                    # 验证会话ID格式
                    if not self._validate_session(session):
                        continue
                    await self.context.send_message(
                        session,
                        message_chain
                    )
                except Exception as e:
                    logger.error(f"GitHub活动监控: 发送通知失败: {e}")

            # 清理临时图片文件
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    logger.debug(f"GitHub活动监控: 已清理临时图片文件: {image_path}")
                except Exception as e:
                    logger.warning(f"GitHub活动监控: 删除图片文件失败: {e}")

            # 记录已推送事件ID
            for event in new_events:
                self.pushed_event_ids.add(event.get("id"))

            # 保存推送记录
            self._save_pushed_event_ids()

        except Exception as e:
            logger.error(f"GitHub活动监控: 处理事件失败: {e}")

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

            # 验证所有会话ID的格式
            valid_sessions = [s for s in target_sessions if self._validate_session(s)]
            if not valid_sessions:
                logger.warning("GitHub活动监控: 没有有效的目标会话ID")
                return

            for username in monitored_users:
                try:
                    # 获取用户最新活动
                    activities = await self.github_api.get_user_events(username)
                    if activities:
                        # 调用新方法处理
                        await self.check_user_activity(username, activities, valid_sessions)
                except Exception as e:
                    logger.error(f"GitHub活动监控: 检查用户 {username} 活动时出错: {e}")
        finally:
            self.is_monitoring = False

    @filter.command("github_test")
    async def test_notification(self, event: AstrMessageEvent):
        """测试GitHub活动通知图片生成"""
        try:
            # 阻止事件继续传播
            event.stop_event()
            
            # 读取测试数据
            test_data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
            if not os.path.exists(test_data_path):
                return event.plain_result("❌ 测试数据文件不存在")

            with open(test_data_path, "r", encoding="utf-8") as f:
                test_events = json.load(f)

            # 只使用最新的5条动态
            test_events = sorted(test_events, key=lambda x: x.get("created_at", ""), reverse=True)[:5]

            # 获取第一个事件的用户信息用于渲染
            first_event = test_events[0]
            actor = first_event.get('actor', {})
            username = actor.get('login', '未知用户')
            avatar_url = actor.get('avatar_url', '')

            # 下载头像并转换为base64
            avatar_base64 = ""
            if avatar_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            avatar_data = await response.read()
                            avatar_base64 = f"data:image/png;base64,{base64.b64encode(avatar_data).decode('utf-8')}"

            # 使用Jinja2渲染HTML
            html_content = self.notification_renderer.render_html(
                username=username,
                avatar_base64=avatar_base64,
                events=test_events
            )

            # 尝试使用HTML渲染系统
            try:
                # 直接使用html_render渲染HTML内容
                image_path = await self.html_render(
                    tmpl=html_content,
                    data={
                        "username": username,
                        "avatar_base64": avatar_base64,
                        "events": test_events
                    },
                    return_url=False
                )

                if image_path:
                    # 直接使用image_result，它会自动处理URL和本地路径
                    return event.image_result(image_path)
            except Exception as e:
                logger.error(f"GitHub活动监控: HTML渲染失败: {e}")

            # 如果没有成功生成图片消息，使用文本消息
            text = self.notification_renderer.create_text_notification(username, test_events)
            return event.plain_result(text)

        except Exception as e:
            logger.error(f"GitHub活动监控: 测试通知失败: {e}")
            return event.plain_result(f"❌ 测试失败: {e}")

    @filter.command("github_status")
    async def github_status(self, event: AstrMessageEvent):
        """显示当前监控状态"""
        monitored_users = self.config.get("monitored_users", [])
        target_sessions = self.config.get("target_sessions", [])
        check_interval = self.config.get("check_interval", 300)
        pushed_count = len(self.pushed_event_ids)
        msg = (
            f"GitHub活动监控插件状态 ♥\n"
            f"监控的用户们: {len(monitored_users)}位大可爱\n"
            f"推送目标: {len(target_sessions)}个频道\n"
            f"检查间隔: {check_interval}秒\n"
            f"已经记录了{pushed_count}条动态呢...诶嘿嘿 ♥"
        )
        yield event.plain_result(msg)

    async def terminate(self):
        """插件卸载时调用"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("GitHub活动监控: 插件已停止...有缘再见呢 ♥")
