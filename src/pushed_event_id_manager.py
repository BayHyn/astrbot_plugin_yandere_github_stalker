"""
事件ID管理器
"""
from typing import Set, Optional
from datetime import datetime
from astrbot.api import logger
from astrbot.api.star import Context


class PushedEventIdManager:
    """事件ID管理器类"""

    def __init__(self, context: Context):
        """
        初始化事件ID管理器

        Args:
            context: AstrBot上下文
        """
        self.context = context
        self.db = self.context.get_db()
        self.table_name = "github_pushed_event_ids"
        logger.debug(f"Yandere Github Stalker: 初始化事件ID管理器，使用数据库存储")

        # 确保数据库中有我们需要的表
        self._ensure_table()

    def _ensure_table(self) -> None:
        """确保数据库中有事件ID表"""
        # 创建事件ID表
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            event_id TEXT PRIMARY KEY,
            pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            if hasattr(self.db, "_exec_sql"):
                self.db._exec_sql(create_table_sql)
            else:
                if hasattr(self.db, "execute"):
                    self.db.execute(create_table_sql)
                    if hasattr(self.db, "commit"):
                        self.db.commit()

            # 创建索引以提高查询性能
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{self.table_name}_pushed_at
            ON {self.table_name} (pushed_at);
            """
            if hasattr(self.db, "_exec_sql"):
                self.db._exec_sql(index_sql)
            else:
                if hasattr(self.db, "execute"):
                    self.db.execute(index_sql)
                    if hasattr(self.db, "commit"):
                        self.db.commit()

            logger.info("Yandere Github Stalker: 事件ID表和索引创建成功或已存在")
        except Exception as e:
            logger.error(f"创建事件ID表或索引失败: {e}")

    def _get_db_cursor(self):
        """获取数据库游标"""
        try:
            return self.db.conn.cursor()
        except Exception as e:
            if hasattr(self.db, "_get_conn") and callable(getattr(self.db, "_get_conn")):
                conn = self.db._get_conn(self.db.db_path)
                return conn.cursor()
            logger.error(f"无法获取数据库连接: {e}")
            raise

    async def add_pushed_event_id(self, event_id: str) -> None:
        """添加事件ID"""
        try:
            # 使用 INSERT OR IGNORE 避免重复插入错误
            insert_sql = f"""
            INSERT OR IGNORE INTO {self.table_name} (event_id, pushed_at)
            VALUES (?, datetime('now'))
            """
            cursor = self._get_db_cursor()
            cursor.execute(insert_sql, (event_id,))
            cursor.connection.commit()
            cursor.close()

            if cursor.rowcount > 0:
                logger.debug(f"Yandere Github Stalker: 添加新事件ID: {event_id}")
            else:
                logger.debug(
                    f"Yandere Github Stalker: 事件ID {event_id} 已存在，跳过添加")
        except Exception as e:
            logger.error(f"添加事件ID失败: {e}")

    async def is_event_pushed(self, event_id: str) -> bool:
        """检查事件ID是否存在"""
        try:
            query_sql = f"SELECT 1 FROM {self.table_name} WHERE event_id = ? LIMIT 1"
            cursor = self._get_db_cursor()
            cursor.execute(query_sql, (event_id,))
            result = cursor.fetchone()
            cursor.close()

            exists = bool(result)
            logger.debug(
                f"Yandere Github Stalker: 检查事件ID {event_id} 是否存在: {exists}")
            return exists
        except Exception as e:
            logger.error(f"检查事件ID是否存在失败: {e}")
            return False

    async def get_pushed_event_count(self) -> int:
        """获取已推送事件的数量"""
        try:
            query_sql = f"SELECT COUNT(*) FROM {self.table_name}"
            cursor = self._get_db_cursor()
            cursor.execute(query_sql)
            result = cursor.fetchone()
            cursor.close()

            count = result[0] if result else 0
            logger.debug(f"Yandere Github Stalker: 当前已推送事件数量：{count}")
            return count
        except Exception as e:
            logger.error(f"获取事件数量失败: {e}")
            return 0

    async def get_last_pushed_time(self) -> Optional[datetime]:
        """获取最后一次推送事件的时间"""
        try:
            query_sql = f"""
            SELECT pushed_at 
            FROM {self.table_name} 
            ORDER BY pushed_at DESC 
            LIMIT 1
            """
            cursor = self._get_db_cursor()
            cursor.execute(query_sql)
            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                # SQLite的时间戳字符串转换为datetime对象
                last_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                logger.debug(f"Yandere Github Stalker: 获取到最后推送时间：{last_time}")
                return last_time
            return None
        except Exception as e:
            logger.error(f"获取最后推送时间失败: {e}")
            return None

    async def cleanup_old_events(self, days: int = 30) -> None:
        """清理指定天数之前的旧事件ID"""
        try:
            delete_sql = f"""
            DELETE FROM {self.table_name}
            WHERE pushed_at < datetime('now', '-' || ? || ' days')
            """
            cursor = self._get_db_cursor()
            cursor.execute(delete_sql, (days,))
            deleted_count = cursor.rowcount
            cursor.connection.commit()
            cursor.close()

            logger.info(
                f"Yandere Github Stalker: 已清理 {deleted_count} 个{days}天前的旧事件ID")
        except Exception as e:
            logger.error(f"清理旧事件ID失败: {e}")

    async def get_all_event_ids(self) -> Set[str]:
        """获取所有事件ID（用于迁移或调试）"""
        try:
            query_sql = f"SELECT event_id FROM {self.table_name}"
            cursor = self._get_db_cursor()
            cursor.execute(query_sql)
            results = cursor.fetchall()
            cursor.close()

            event_ids = {row[0] for row in results}
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

            cursor = self._get_db_cursor()
            cursor.execute("BEGIN TRANSACTION")
            try:
                insert_sql = f"INSERT OR IGNORE INTO {self.table_name} (event_id) VALUES (?)"
                for event_id in file_ids:
                    cursor.execute(insert_sql, (event_id,))
                cursor.connection.commit()
                logger.info(f"成功从文件迁移了 {len(file_ids)} 个事件ID到数据库")
                return True
            except Exception as e:
                cursor.connection.rollback()
                logger.error(f"迁移过程中出错，已回滚: {e}")
                return False
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"从文件迁移数据失败: {e}")
            return False

    def close(self):
        """关闭管理器，释放资源"""
        logger.info("Yandere Github Stalker: 关闭事件ID管理器...")
        try:
            self.db = None
            logger.info("Yandere Github Stalker: 事件ID管理器已成功关闭")
        except Exception as e:
            logger.error(f"关闭事件ID管理器时出错: {e}")
