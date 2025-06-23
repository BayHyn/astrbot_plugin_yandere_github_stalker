"""
Message sending functionality
"""
import os
from typing import List
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.message_type import MessageType
from astrbot.core.message.components import Image
from astrbot.api.message_components import Plain, Image as CompImage

class MessageSender:
    def __init__(self, context):
        self.context = context

    def _format_session_id(self, session_id: str) -> str:
        """格式化会话ID，确保包含必要的平台信息"""
        if ':' not in session_id:
            # 如果没有平台信息，默认添加discord平台和GroupMessage类型
            return f"discord:{MessageType.GROUP_MESSAGE.value}:{session_id}"
        return session_id

    def build_message_chain(self, content):
        """
        自动构建消息链，兼容文本、图片、dict等多种类型
        """
        if isinstance(content, MessageChain):
            return content
        elif isinstance(content, str):
            return MessageChain([Plain(content)])
        elif isinstance(content, dict):
            # 支持dict类型的图片或其他组件
            if content.get("type") == "image" and content.get("path"):
                img = Image.fromFileSystem(content["path"])
                if img:
                    return MessageChain([img])
                else:
                    # 图片加载失败，回退为文本提示
                    return MessageChain([Plain("[图片加载失败]")])
            # 其他dict类型可扩展
            return MessageChain([Plain(str(content))])
        elif isinstance(content, list):
            # 支持混合消息链
            chain = []
            for item in content:
                if isinstance(item, str):
                    chain.append(Plain(item))
                elif isinstance(item, dict) and item.get("type") == "image" and item.get("path"):
                    img = Image.fromFileSystem(item["path"])
                    if img:
                        chain.append(img)
                    else:
                        chain.append(Plain("[图片加载失败]"))
                # 可扩展更多类型
            if not chain:
                chain = [Plain("[空消息]")]
            return MessageChain(chain)
        else:
            return MessageChain([Plain(str(content))])

    async def send_notification(self, target_sessions: list, message):
        """发送通知到目标会话，自动兼容多种消息类型"""
        message_chain = self.build_message_chain(message)
        for session in target_sessions:
            try:
                session_id = self._format_session_id(session)
                await self.context.send_message(session_id, message_chain)
            except Exception as e:
                logger.error(f"GitHub User Stalker: 向会话 {session} 发送通知失败: {str(e)}")

    async def send_image_notification(self, target_sessions: list, image_path: str):
        """发送图片通知到目标会话（兼容StarMonitor方式，修复NoneType问题）"""
        img = CompImage.fromFileSystem(image_path)
        if img is not None:
            message_chain = MessageChain([img])
        else:
            message_chain = MessageChain([Plain(f"[图片发送失败: {image_path}]")])
        for session in target_sessions:
            success = False
            try:
                session_id = self._format_session_id(session)
                await self.context.send_message(session_id, message_chain)
                success = True
            except Exception as e:
                logger.error(f"GitHub User Stalker: 向会话 {session} 发送图片通知失败: {str(e)}")
            finally:
                filename = os.path.basename(image_path)
                if success and filename.startswith("github_notification_") and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        logger.debug(f"GitHub User Stalker: 已清理临时图片文件: {image_path}")
                    except Exception as e:
                        logger.warning(f"GitHub User Stalker: 删除图片文件失败: {e}")

    async def send_startup_notification(self, users: List[str], target_sessions: List[str], check_interval: int):
        """发送启动通知"""
        if not target_sessions:
            return
        
        message = "🚀 GitHub用户活动监控插件已启动\n\n"
        if users:
            message += f"正在监控 {len(users)} 个用户:\n"
            for username in users[:5]:
                message += f"• @{username}\n"
            if len(users) > 5:
                message += f"... 以及其他 {len(users) - 5} 个用户\n"
        else:
            message += "⚠️ 未配置监控用户\n"
        
        message += f"\n检查间隔: {check_interval} 秒"
        
        await self.send_notification(target_sessions, message) 