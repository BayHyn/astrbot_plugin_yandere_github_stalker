"""
事件ID管理器
"""
import os
import json
import asyncio
from typing import Set
from astrbot.api import logger

class PushedEventIdManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = asyncio.Lock()
        logger.debug(f"Yandere Github Stalker: 初始化事件ID管理器，文件路径：{file_path}")
        self.ids: Set[str] = self._load()
        logger.debug(f"Yandere Github Stalker: 已加载 {len(self.ids)} 个已推送事件ID")
        if self.ids:
            logger.debug(f"Yandere Github Stalker: 已有事件ID示例：{list(self.ids)[:5]}")

    def _load(self) -> Set[str]:
        """加载已推送的事件ID"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    ids = set(json.load(f))
                    logger.debug(f"Yandere Github Stalker: 从文件 {self.file_path} 加载了 {len(ids)} 个事件ID")
                    if ids:
                        logger.debug(f"Yandere Github Stalker: 加载的事件ID示例：{list(ids)[:5]}")
                    return ids
            except Exception as e:
                logger.error(f"Yandere Github Stalker: 加载事件ID失败: {e}，文件路径：{self.file_path}")
                return set()
        logger.debug(f"Yandere Github Stalker: 事件ID文件 {self.file_path} 不存在，创建新的集合")
        return set()

    async def add_pushed_event_id(self, event_id: str) -> None:
        """添加事件ID"""
        async with self._lock:
            was_present = event_id in self.ids
            self.ids.add(event_id)
            await self.save()
            if was_present:
                logger.debug(f"Yandere Github Stalker: 事件ID {event_id} 已存在，跳过添加")
            else:
                logger.debug(f"Yandere Github Stalker: 添加新事件ID: {event_id}，当前总数：{len(self.ids)}")

    async def is_event_pushed(self, event_id: str) -> bool:
        """检查事件ID是否存在"""
        async with self._lock:
            result = event_id in self.ids
            logger.debug(f"Yandere Github Stalker: 检查事件ID {event_id} 是否存在: {result}，当前总数：{len(self.ids)}")
            return result

    async def get_pushed_event_count(self) -> int:
        """获取已推送事件的数量"""
        async with self._lock:
            count = len(self.ids)
            logger.debug(f"Yandere Github Stalker: 当前已推送事件数量：{count}")
            return count

    async def save(self) -> None:
        """保存事件ID到文件"""
        try:
            async with self._lock:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    id_list = list(self.ids)
                    json.dump(id_list, f)
                    logger.debug(f"Yandere Github Stalker: 保存了 {len(self.ids)} 个事件ID到文件 {self.file_path}")
                    if id_list:
                        logger.debug(f"Yandere Github Stalker: 最新保存的事件ID示例：{id_list[:5]}")
        except Exception as e:
            logger.error(f"Yandere Github Stalker: 保存事件ID失败: {e}，文件路径：{self.file_path}")

    def __len__(self) -> int:
        return len(self.ids) 