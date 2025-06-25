"""
事件处理器
"""
from typing import List, Dict, Tuple
from astrbot.api import logger
from .pushed_event_id_manager import PushedEventIdManager

class EventProcessor:
    def __init__(self, event_limit: int, pushed_event_ids_manager: PushedEventIdManager, config_manager):
        self.event_limit = event_limit
        self.pushed_event_ids_manager = pushed_event_ids_manager
        self.config_manager = config_manager
        logger.debug(f"Yandere Github Stalker: 事件处理器初始化，事件限制：{event_limit}")

    async def process_events(self, events: List[Dict]) -> List[Dict]:
        """处理事件列表，返回需要推送的新事件"""
        logger.debug(f"Yandere Github Stalker: 处理 {len(events)} 条排序后的事件")
        
        if events:
            earliest_event = events[-1]  # events 按时间倒序排列
            latest_event = events[0]
            logger.debug(f"Yandere Github Stalker: 最早事件时间：{earliest_event.get('created_at')}，最新事件时间：{latest_event.get('created_at')}")

        # 获取当前已推送的事件数量
        pushed_count = await self.pushed_event_ids_manager.get_pushed_event_count()
        logger.debug(f"Yandere Github Stalker: 当前已推送事件数：{pushed_count}")

        # 获取事件限制数量
        event_limit = self.config_manager.get_event_limit()
        logger.debug(f"Yandere Github Stalker: 事件限制数量：{event_limit}")

        new_events = []
        for event in events:
            event_id = event.get("id")
            event_type = event.get("type")
            event_time = event.get("created_at")
            
            logger.debug(f"Yandere Github Stalker: 检查事件 {event_id}，类型：{event_type}，时间：{event_time}")
            
            # 检查事件是否已经推送过
            is_pushed = await self.pushed_event_ids_manager.is_event_pushed(event_id)
            logger.debug(f"Yandere Github Stalker: 检查事件ID {event_id} 是否存在: {is_pushed}，当前总数：{pushed_count}")
            
            if not is_pushed:
                logger.debug(f"Yandere Github Stalker: 发现新事件 {event_id}，类型：{event_type}")
                new_events.append(event)

                # 检查是否达到事件限制
                if event_limit > 0 and len(new_events) >= event_limit:
                    logger.debug(f"Yandere Github Stalker: 达到事件限制 {event_limit}，停止处理")
                    break

        logger.info(f"Yandere Github Stalker: 发现 {len(new_events)} 条新事件，类型：{[e.get('type') for e in new_events]} ")
        return new_events[:event_limit] if event_limit > 0 else new_events

    async def mark_event_as_pushed(self, event_id: str) -> None:
        """将事件标记为已推送"""
        await self.pushed_event_ids_manager.add_pushed_event_id(event_id)
        logger.debug(f"Yandere Github Stalker: 已将事件 {event_id} 标记为已推送")

    async def mark_event_as_ignored(self, event_id: str) -> None:
        """将事件标记为已忽略（例如因为模板缺失）"""
        await self.pushed_event_ids_manager.add_pushed_event_id(event_id)
        logger.debug(f"Yandere Github Stalker: 已将事件 {event_id} 标记为已忽略") 