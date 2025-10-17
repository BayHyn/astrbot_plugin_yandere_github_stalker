"""
事件ID管理器 - AstrBot v4.x 兼容版本
"""
from typing import Set, Optional
from datetime import datetime
from astrbot.api import logger
from astrbot.api.star import Context
from sqlalchemy import text


class PushedEventIdManager:
    """事件ID管理器类 - 适配 AstrBot v4.x 异步数据库"""

    def __init__(self, context: Context):
        """
        初始化事件ID管理器

        Args:
            context: AstrBot上下文
        """
        self.context = context
        self.db = self.context.get_db()
        self.table_name = "github_pushed_event_ids"
        self._table_ensured = False
        logger.debug(f"Yandere Github Stalker: 初始化事件ID管理器，使用数据库存储")

    async def _ensure_table_once(self) -> None:
        """确保表只被初始化一次（延迟初始化模式）"""
        if not self._table_ensured:
            await self._ensure_table()
            self._table_ensured = True

    async def _ensure_table(self) -> None:
        """确保数据库中有事件ID表，并在需要时升级表结构"""
        try:
            async with self.db.get_db() as session:
                async with session.begin():
                    # 检查表是否存在
                    check_table_sql = text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=:table_name;
                    """)
                    result = await session.execute(check_table_sql, {"table_name": self.table_name})
                    table_exists = result.fetchone() is not None

                    if not table_exists:
                        # 如果表不存在，创建新表
                        create_table_sql = text(f"""
                            CREATE TABLE {self.table_name} (
                                event_id TEXT,
                                username TEXT,
                                pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (event_id, username)
                            );
                        """)
                        await session.execute(create_table_sql)
                        logger.info("Yandere Github Stalker: 事件ID表创建成功")
                    else:
                        # 如果表存在，检查是否需要升级结构
                        check_column_sql = text("""
                            SELECT sql FROM sqlite_master
                            WHERE type='table' AND name=:table_name;
                        """)
                        result = await session.execute(check_column_sql, {"table_name": self.table_name})
                        row = result.fetchone()
                        table_schema = row[0] if row else ""

                        if 'username' not in table_schema:
                            # 需要升级表结构
                            logger.info("Yandere Github Stalker: 检测到旧版本表结构，开始升级...")
                            
                            # 1. 重命名旧表
                            await session.execute(text(f"ALTER TABLE {self.table_name} RENAME TO {self.table_name}_old;"))
                            
                            # 2. 创建新表
                            create_table_sql = text(f"""
                                CREATE TABLE {self.table_name} (
                                    event_id TEXT,
                                    username TEXT,
                                    pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    PRIMARY KEY (event_id, username)
                                );
                            """)
                            await session.execute(create_table_sql)
                            
                            # 3. 迁移数据（将旧数据迁移到新表，使用空字符串作为默认用户名）
                            migrate_sql = text(f"""
                                INSERT INTO {self.table_name} (event_id, username, pushed_at)
                                SELECT event_id, '' as username, pushed_at
                                FROM {self.table_name}_old;
                            """)
                            await session.execute(migrate_sql)
                            
                            # 4. 删除旧表
                            await session.execute(text(f"DROP TABLE {self.table_name}_old;"))
                            
                            logger.info("Yandere Github Stalker: 表结构升级完成")

                    # 创建或更新索引
                    index_sql = text(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_pushed_at
                        ON {self.table_name} (username, pushed_at);
                    """)
                    await session.execute(index_sql)

                    logger.info("Yandere Github Stalker: 事件ID表和索引检查/更新完成")
        except Exception as e:
            logger.error(f"创建或升级事件ID表失败: {e}")
            raise

    async def add_pushed_event_id(self, event_id: str, username: str, pushed_at: str = None) -> bool:
        """添加事件ID
        Args:
            event_id: 要添加的事件ID
            username: GitHub用户名
            pushed_at: 事件发生时间（ISO格式字符串），如 None 则用当前时间
        Returns:
            bool: 是否成功添加
        """
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                async with session.begin():
                    if pushed_at is None:
                        insert_sql = text(f"""
                            INSERT OR IGNORE INTO {self.table_name} (event_id, username, pushed_at)
                            VALUES (:event_id, :username, datetime('now'))
                        """)
                        params = {"event_id": event_id, "username": username}
                    else:
                        # 格式转换：2024-01-01T12:00:00Z -> 2024-01-01 12:00:00
                        pushed_at_sqlite = pushed_at.replace("T", " ").replace("Z", "")
                        insert_sql = text(f"""
                            INSERT OR IGNORE INTO {self.table_name} (event_id, username, pushed_at)
                            VALUES (:event_id, :username, :pushed_at)
                        """)
                        params = {"event_id": event_id, "username": username, "pushed_at": pushed_at_sqlite}

                    result = await session.execute(insert_sql, params)
                    success = result.rowcount > 0
                    
                    if success:
                        logger.debug(f"Yandere Github Stalker: 添加新事件ID: {event_id} (用户: {username})")
                    else:
                        logger.debug(
                            f"Yandere Github Stalker: 事件ID {event_id} (用户: {username}) 已存在，跳过添加")

            return True
        except Exception as e:
            logger.error(f"添加事件ID失败: {e}")
            return False

    async def is_event_pushed(self, event_id: str, username: str) -> bool:
        """检查事件ID是否存在
        
        Args:
            event_id: 事件ID
            username: GitHub用户名
        """
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                query_sql = text(f"SELECT 1 FROM {self.table_name} WHERE event_id = :event_id AND username = :username LIMIT 1")
                result = await session.execute(query_sql, {"event_id": event_id, "username": username})
                row = result.fetchone()

                exists = bool(row)
                logger.debug(
                    f"Yandere Github Stalker: 检查事件ID {event_id} (用户: {username}) 是否存在: {exists}")
                return exists
        except Exception as e:
            logger.error(f"检查事件ID是否存在失败: {e}")
            return False

    async def get_pushed_event_count(self, username: str = None) -> int:
        """获取已推送事件的数量
        
        Args:
            username: 可选的GitHub用户名，如果提供则只统计该用户的事件
        """
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                if username:
                    query_sql = text(f"SELECT COUNT(*) FROM {self.table_name} WHERE username = :username")
                    result = await session.execute(query_sql, {"username": username})
                else:
                    query_sql = text(f"SELECT COUNT(*) FROM {self.table_name}")
                    result = await session.execute(query_sql)
                
                row = result.fetchone()
                count = row[0] if row else 0
                
                if username:
                    logger.debug(f"Yandere Github Stalker: 用户 {username} 当前已推送事件数量：{count}")
                else:
                    logger.debug(f"Yandere Github Stalker: 当前已推送事件总数量：{count}")
                return count
        except Exception as e:
            logger.error(f"获取事件数量失败: {e}")
            return 0

    async def get_last_pushed_time(self, username: str) -> Optional[datetime]:
        """获取最后一次推送事件的时间
        
        Args:
            username: GitHub用户名
        """
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                query_sql = text(f"""
                    SELECT pushed_at 
                    FROM {self.table_name} 
                    WHERE username = :username
                    ORDER BY pushed_at DESC 
                    LIMIT 1
                """)
                result = await session.execute(query_sql, {"username": username})
                row = result.fetchone()

                if row and row[0]:
                    # SQLite的时间戳字符串转换为datetime对象
                    last_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    logger.debug(f"Yandere Github Stalker: 获取到用户 {username} 最后推送时间：{last_time}")
                    return last_time
                return None
        except Exception as e:
            logger.error(f"获取最后推送时间失败: {e}")
            return None

    async def cleanup_old_events(self, days: int = 30) -> bool:
        """清理指定天数之前的旧事件ID，并回收所有未来时间的事件ID"""
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                async with session.begin():
                    # 1. 清理过期事件
                    delete_sql = text(f"""
                        DELETE FROM {self.table_name}
                        WHERE pushed_at < datetime('now', '-' || :days || ' days')
                    """)
                    result1 = await session.execute(delete_sql, {"days": days})
                    deleted_count = result1.rowcount

                    # 2. 清理未来时间的事件
                    delete_future_sql = text(f"""
                        DELETE FROM {self.table_name}
                        WHERE pushed_at > datetime('now')
                    """)
                    result2 = await session.execute(delete_future_sql)
                    deleted_future_count = result2.rowcount

                    logger.info(
                        f"Yandere Github Stalker: 已清理 {deleted_count} 个{days}天前的旧事件ID，{deleted_future_count} 个未来时间事件ID")
            return True
        except Exception as e:
            logger.error(f"清理旧事件ID失败: {e}")
            return False

    async def get_all_event_ids(self, username: str = None) -> Set[str]:
        """获取所有事件ID（用于迁移或调试）
        
        Args:
            username: 可选的GitHub用户名，如果提供则只获取该用户的事件ID
        """
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                if username:
                    query_sql = text(f"SELECT event_id FROM {self.table_name} WHERE username = :username")
                    result = await session.execute(query_sql, {"username": username})
                else:
                    query_sql = text(f"SELECT event_id FROM {self.table_name}")
                    result = await session.execute(query_sql)
                
                results = result.fetchall()
                event_ids = {row[0] for row in results}
                
                if username:
                    logger.debug(f"Yandere Github Stalker: 获取到用户 {username} 的 {len(event_ids)} 个事件ID")
                else:
                    logger.debug(f"Yandere Github Stalker: 获取到 {len(event_ids)} 个事件ID")
                return event_ids
        except Exception as e:
            logger.error(f"获取所有事件ID失败: {e}")
            return set()

    async def migrate_from_file(self, file_path: str) -> bool:
        """从文件迁移数据到数据库"""
        import json
        import os

        try:
            if not os.path.exists(file_path):
                logger.warning(f"源文件不存在: {file_path}")
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                file_ids = set(json.load(f))

            if not file_ids:
                logger.info("源文件为空，无需迁移")
                return True

            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                async with session.begin():
                    insert_sql = text(f"INSERT OR IGNORE INTO {self.table_name} (event_id, username) VALUES (:event_id, '')")
                    for event_id in file_ids:
                        await session.execute(insert_sql, {"event_id": event_id})
                    
                    logger.info(f"成功从文件迁移了 {len(file_ids)} 个事件ID到数据库")
            return True
        except Exception as e:
            logger.error(f"从文件迁移数据失败: {e}")
            return False

    async def _get_count(self) -> int:
        """内部方法：异步获取事件总数"""
        try:
            await self._ensure_table_once()
            
            async with self.db.get_db() as session:
                query_sql = text(f"SELECT COUNT(*) FROM {self.table_name}")
                result = await session.execute(query_sql)
                row = result.fetchone()
                count = row[0] if row else 0
                logger.debug(f"Yandere Github Stalker: 当前总事件数量：{count}")
                return count
        except Exception as e:
            logger.error(f"获取事件总数失败: {e}")
            return 0

    def __len__(self) -> int:
        """获取事件总数
        
        Returns:
            int: 事件总数
        
        注意：这是一个同步方法包装器，建议直接使用 _get_count() 异步方法
        """
        import asyncio
        try:
            # 尝试获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，无法使用 asyncio.run
                logger.warning("Yandere Github Stalker: __len__ 在事件循环中被调用，返回 0")
                return 0
            except RuntimeError:
                # 没有运行中的事件循环，可以创建新的
                return asyncio.run(self._get_count())
        except Exception as e:
            logger.error(f"获取事件总数失败: {e}")
            return 0

    def close(self):
        """关闭管理器，释放资源"""
        logger.info("Yandere Github Stalker: 关闭事件ID管理器...")
        try:
            self.db = None
            logger.info("Yandere Github Stalker: 事件ID管理器已成功关闭")
        except Exception as e:
            logger.error(f"关闭事件ID管理器时出错: {e}")
