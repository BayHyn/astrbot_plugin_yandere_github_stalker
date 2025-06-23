"""
GitHub API related functionality
"""
import aiohttp
from typing import Optional, List, Dict
from datetime import datetime
from astrbot.api import logger

class GitHubAPI:
    def __init__(self, token: str = ""):
        self.token = token.strip()
        self.headers = {
            'User-Agent': 'AstrBot-GitHub-User-Stalker/1.0.0',
            'Accept': 'application/vnd.github.v3+json'
        }
        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'

    async def get_user_events(self, username: str) -> Optional[List[dict]]:
        """获取用户的GitHub活动"""
        try:
            url = f"https://api.github.com/users/{username}/events"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"GitHub User Stalker: 用户 {username} 不存在")
                        return None
                    else:
                        logger.warning(f"GitHub User Stalker: GitHub API返回状态码 {response.status}")
                        return None
        except Exception as e:
            logger.error(f"GitHub User Stalker: 获取用户 {username} 活动失败: {e}")
            return None

    async def get_user_info(self, username: str) -> Optional[dict]:
        """获取用户信息"""
        try:
            url = f"https://api.github.com/users/{username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"GitHub User Stalker: 获取用户信息失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"GitHub User Stalker: 获取用户信息失败: {e}")
            return None

    async def download_avatar_base64(self, avatar_url: str) -> Optional[str]:
        """下载头像并转换为base64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        import base64
                        return base64.b64encode(avatar_data).decode('utf-8')
        except Exception as e:
            logger.error(f"GitHub User Stalker: 下载头像失败: {e}")
        return None 