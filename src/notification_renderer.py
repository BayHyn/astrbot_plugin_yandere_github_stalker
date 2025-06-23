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
        
        # 确保模板文件存在
        self._ensure_templates_exist(template_dir)

    def _ensure_templates_exist(self, template_dir: str):
        """确保模板文件存在"""
        # 主模板
        main_template_path = os.path.join(template_dir, 'notification.html')
        if not os.path.exists(main_template_path):
            with open(main_template_path, 'w', encoding='utf-8') as f:
                f.write(self._get_main_template())
        
        # 事件项模板
        event_template_path = os.path.join(template_dir, 'event_item.html')
        if not os.path.exists(event_template_path):
            with open(event_template_path, 'w', encoding='utf-8') as f:
                f.write(self._get_event_item_template())

    def _get_main_template(self) -> str:
        """获取主模板内容"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    margin: 0;
                    padding: 40px;
                    font-family: 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
                    background: linear-gradient(135deg, #FF69B4 0%, #FFB6C1 100%);
                    min-height: 520px;
                    box-sizing: border-box;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(255,105,180,0.3);
                    max-width: 720px;
                    margin: 0 auto;
                }
                .title {
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    color: #FF1493;
                    margin-bottom: 30px;
                }
                .user-info {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #FFF0F5;
                    border-radius: 12px;
                    border: 2px solid #FFB6C1;
                }
                .avatar {
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    border: 3px solid #FF69B4;
                }
                .username {
                    font-size: 24px;
                    font-weight: bold;
                    color: #FF1493;
                }
                .event-item {
                    display: flex;
                    gap: 20px;
                    padding: 20px;
                    background: #FFF0F5;
                    border-radius: 12px;
                    margin-bottom: 15px;
                    border: 2px solid #FFB6C1;
                    transition: all 0.3s ease;
                }
                .event-item:hover {
                    transform: translateX(5px);
                    border-color: #FF69B4;
                }
                .event-type {
                    font-size: 14px;
                    font-weight: bold;
                    color: #FF69B4;
                    padding: 8px 12px;
                    background: rgba(255,105,180,0.1);
                    border-radius: 8px;
                    white-space: nowrap;
                }
                .event-info {
                    flex: 1;
                }
                .repo-name {
                    font-size: 16px;
                    font-weight: bold;
                    color: #FF1493;
                    margin-bottom: 8px;
                }
                .event-description {
                    font-size: 14px;
                    color: #FF69B4;
                    line-height: 1.6;
                }
                .event-time {
                    font-size: 12px;
                    color: #FFB6C1;
                    margin-top: 8px;
                }
                .heart {
                    position: absolute;
                    font-size: 24px;
                    color: #FF69B4;
                    animation: float 2s ease-in-out infinite;
                }
                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">GitHub Activity Monitor ♥</div>
                <div class="user-info">
                    <img class="avatar" src="{{ avatar_base64 or default_avatar }}" alt="User Avatar">
                    <div class="username">{{ username }}君的动态 ♥</div>
                </div>
                {% for event in events %}
                    {% include 'event_item.html' %}
                {% endfor %}
            </div>
        </body>
        </html>
        """

    def _get_event_item_template(self) -> str:
        """获取事件项模板内容"""
        return """
        <div class="event-item">
            <div class="event-type">{{ event.type }}</div>
            <div class="event-info">
                <div class="repo-name">{{ event.repo_name }}</div>
                <div class="event-description">{{ event.description }}</div>
                <div class="event-time">{{ event.created_at }}</div>
            </div>
        </div>
        """

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
