"""
Notification rendering functionality
"""
from typing import List
from datetime import datetime


class NotificationRenderer:
    # HTML模板
    NOTIFICATION_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                margin: 0;
                padding: 40px;
                font-family: 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #6e8efb 0%, #a777e3 100%);
                min-height: 520px;
                box-sizing: border-box;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                max-width: 720px;
                margin: 0 auto;
            }
            .title {
                font-size: 32px;
                font-weight: bold;
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }
            .user-info {
                display: flex;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
            }
            .avatar {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                border: 3px solid #6e8efb;
            }
            .username {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }
            .event-item {
                display: flex;
                gap: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
                margin-bottom: 15px;
                transition: transform 0.2s;
            }
            .event-item:hover {
                transform: translateX(5px);
            }
            .event-type {
                font-size: 14px;
                font-weight: bold;
                color: #6e8efb;
                padding: 8px 12px;
                background: rgba(110, 142, 251, 0.1);
                border-radius: 8px;
                white-space: nowrap;
            }
            .event-info {
                flex: 1;
            }
            .repo-name {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
            }
            .event-description {
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
            }
            .event-time {
                font-size: 12px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title">
                GitHub 用户活动提醒
            </div>
            
            <div class="user-info">
                <img class="avatar" src="{{ avatar_base64 or default_avatar }}" alt="avatar" />
                <div class="username">@{{ username }}</div>
            </div>
            
            {% for event in events[:5] %}
            <div class="event-item">
                <div class="event-type">{{ event.type }}</div>
                <div class="event-info">
                    <div class="repo-name">{{ event.repo.name }}</div>
                    <div class="event-description">{{ event.description }}</div>
                    <div class="event-time">{{ event.created_at }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """

    # 默认头像（Base64编码的SVG）
    DEFAULT_AVATAR = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiNEREREREQiLz4KPHN2ZyB4PSIyNSIgeT0iMjUiIHdpZHRoPSIzMCIgaGVpZ2h0PSIzMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSIjOTk5OTk5Ij4KPHA+VXNlcjwvcD4KPHN2Zz4KPC9zdmc+'

    @staticmethod
    def get_event_description(event: dict) -> str:
        """根据事件类型生成描述"""
        event_type = event['type']
        payload = event.get('payload', {})

        if event_type == 'PushEvent':
            commits = payload.get('commits', [])
            commit_count = len(commits)
            return f"推送了 {commit_count} 个提交"

        elif event_type == 'CreateEvent':
            ref_type = payload.get('ref_type', '')
            ref = payload.get('ref', '')
            return f"创建了 {ref_type} {ref}"

        elif event_type == 'IssuesEvent':
            action = payload.get('action', '')
            issue_title = payload.get('issue', {}).get('title', '')
            return f"{action} issue: {issue_title}"

        elif event_type == 'PullRequestEvent':
            action = payload.get('action', '')
            pr_title = payload.get('pull_request', {}).get('title', '')
            return f"{action} PR: {pr_title}"

        elif event_type == 'WatchEvent':
            return "标星了该仓库"

        elif event_type == 'ForkEvent':
            return "Fork了该仓库"

        return f"触发了 {event_type} 事件"

    @staticmethod
    def create_text_notification(username: str, events: List[dict]) -> str:
        """创建文本通知内容"""
        message = f"👤 GitHub用户 @{username} 有新活动！\n\n"

        for event in events[:5]:  # 最多显示5个事件
            event_type = event['type']
            repo_name = event['repo']['name']
            created_at = datetime.strptime(
                event['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
            description = NotificationRenderer.get_event_description(event)

            message += f"📌 {event_type}\n"
            message += f"📁 {repo_name}\n"
            message += f"📝 {description}\n"
            message += f"🕒 {created_at}\n\n"

        if len(events) > 5:
            message += f"... 以及其他 {len(events) - 5} 个活动"

        return message
