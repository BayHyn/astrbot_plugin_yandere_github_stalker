"""
Notification rendering functionality
"""
from typing import List
from datetime import datetime
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .yandere_templates import YandereTemplates


class NotificationRenderer:
    def __init__(self, custom_templates: dict = None):
        """初始化渲染器"""
        self.yandere_templates = YandereTemplates(custom_templates)

        # 设置Jinja2环境
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        os.makedirs(template_dir, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def get_event_description(self, event: dict) -> str:
        """根据事件类型生成描述"""
        return self.yandere_templates.format_event_message(event)

    def render_html(self, username: str, avatar_base64: str, events: List[dict]) -> str:
        """
        渲染HTML内容
        :param username: 用户名
        :param avatar_base64: 头像的base64编码
        :param events: 事件列表
        :return: 渲染后的HTML字符串
        """
        template = self.jinja_env.get_template('notification.html')

        # 处理事件数据
        processed_events = []
        for event in events:
            created_at = datetime.strptime(
                event['created_at'],
                "%Y-%m-%dT%H:%M:%SZ"
            ).strftime("%Y-%m-%d %H:%M:%S")

            processed_events.append({
                'type': event['type'],
                'repo_name': event['repo']['name'],
                'description': self.get_event_description(event),
                'created_at': created_at
            })

        # 渲染模板
        return template.render(
            username=username,
            avatar_base64=avatar_base64,
            default_avatar=self.DEFAULT_AVATAR,
            events=processed_events
        )

    @staticmethod
    def create_text_notification(username: str, events: List[dict]) -> str:
        """创建文本通知内容"""
        yandere = YandereTemplates()
        message = f"啊啊啊！{username}君又有新的动态了呢！♥\n\n"

        for event in events[:5]:  # 最多显示5个事件
            message += f"{yandere.format_event_message(event)}\n\n"

        if len(events) > 5:
            message += f"还有{len(events) - 5}个动态...{username}君真是太活跃了呢 ♥"

        return message

    # 默认头像（Base64编码的SVG）
    DEFAULT_AVATAR = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiNEREREREQiLz4KPHN2ZyB4PSIyNSIgeT0iMjUiIHdpZHRoPSIzMCIgaGVpZ2h0PSIzMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSIjOTk5OTk5Ij4KPHA+VXNlcjwvcD4KPHN2Zz4KPC9zdmc+'
