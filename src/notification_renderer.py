"""
Notification rendering functionality
"""
import os
import time
from typing import List, Optional
from datetime import datetime
from playwright.async_api import async_playwright
from astrbot.api import logger
import aiohttp

class NotificationRenderer:
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
            created_at = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
            description = NotificationRenderer.get_event_description(event)
            
            message += f"📌 {event_type}\n"
            message += f"📁 {repo_name}\n"
            message += f"📝 {description}\n"
            message += f"🕒 {created_at}\n\n"
        
        if len(events) > 5:
            message += f"... 以及其他 {len(events) - 5} 个活动"
        
        return message

    @staticmethod
    async def create_html_notification(username: str, events: List[dict], avatar_base64: str = "") -> str:
        """创建HTML通知内容"""
        # 生成事件HTML
        events_html = ""
        for event in events[:5]:  # 最多显示5个事件
            event_type = event['type']
            repo_name = event['repo']['name']
            created_at = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
            description = NotificationRenderer.get_event_description(event)
            
            events_html += f"""
            <div class="event-item">
                <div class="event-type">{event_type}</div>
                <div class="event-info">
                    <div class="repo-name">{repo_name}</div>
                    <div class="event-description">{description}</div>
                    <div class="event-time">{created_at}</div>
                </div>
            </div>
            """
        
        # 创建HTML模板
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    margin: 0;
                    padding: 40px;
                    font-family: 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
                    background: linear-gradient(135deg, #6e8efb 0%, #a777e3 100%);
                    min-height: 520px;
                    box-sizing: border-box;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                    max-width: 720px;
                    margin: 0 auto;
                }}
                .title {{
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    color: #2c3e50;
                    margin-bottom: 30px;
                }}
                .user-info {{
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 12px;
                }}
                .avatar {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    border: 3px solid #6e8efb;
                }}
                .username {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .event-item {{
                    display: flex;
                    gap: 20px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 12px;
                    margin-bottom: 15px;
                    transition: transform 0.2s;
                }}
                .event-item:hover {{
                    transform: translateX(5px);
                }}
                .event-type {{
                    font-size: 14px;
                    font-weight: bold;
                    color: #6e8efb;
                    padding: 8px 12px;
                    background: rgba(110, 142, 251, 0.1);
                    border-radius: 8px;
                    white-space: nowrap;
                }}
                .event-info {{
                    flex: 1;
                }}
                .repo-name {{
                    font-size: 16px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 8px;
                }}
                .event-description {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 8px;
                }}
                .event-time {{
                    font-size: 12px;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">
                    GitHub 用户活动提醒
                </div>
                
                <div class="user-info">
                    <img class="avatar" src="{avatar_base64 or 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiNEREREREQiLz4KPHN2ZyB4PSIyNSIgeT0iMjUiIHdpZHRoPSIzMCIgaGVpZ2h0PSIzMCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSIjOTk5OTk5Ij4KPHA+VXNlcjwvcD4KPHN2Zz4KPC9zdmc+'}" alt="avatar" />
                    <div class="username">@{username}</div>
                </div>
                
                {events_html}
            </div>
        </body>
        </html>
        """

    @staticmethod
    async def render_html_to_image(html_content: str) -> str:
        """使用Playwright将HTML渲染为图片"""
        try:
            # 确保data目录存在
            if not os.path.exists("data"):
                os.makedirs("data")
            
            image_path = f"data/github_notification_{int(time.time())}.png"
            
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 设置视口大小
                await page.set_viewport_size({"width": 800, "height": 600})
                
                # 设置HTML内容
                await page.set_content(html_content)
                
                # 等待页面加载完成
                await page.wait_for_load_state('networkidle')
                
                # 截图
                await page.screenshot(
                    path=image_path,
                    full_page=True,
                    type='png'
                )
                
                await browser.close()
                
                logger.info(f"GitHub User Stalker: 成功生成通知图片: {image_path}")
                return image_path
                
        except Exception as e:
            logger.error(f"GitHub User Stalker: Playwright渲染失败: {e}")
            return ""

    async def render_event_notification(self, event: dict) -> str:
        """渲染单个事件的通知图片"""
        try:
            # 获取事件相关信息
            actor = event.get('actor', {})
            username = actor.get('login', '未知用户')
            avatar_url = actor.get('avatar_url', '')
            
            # 下载头像并转换为base64
            avatar_base64 = ""
            if avatar_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            avatar_data = await response.read()
                            import base64
                            avatar_base64 = f"data:image/png;base64,{base64.b64encode(avatar_data).decode('utf-8')}"
            
            # 创建HTML通知
            html_content = await self.create_html_notification(username, [event], avatar_base64)
            
            # 渲染为图片
            return await self.render_html_to_image(html_content)
            
        except Exception as e:
            logger.error(f"GitHub User Stalker: 渲染事件通知失败: {e}")
            return "" 