"""
配置管理器
"""
from typing import Any, List, Dict
from astrbot.api import AstrBotConfig

class ConfigManager:
    # 事件类型映射
    EVENT_TYPE_MAPPING = {
        'push': 'PushEvent',
        'issues': 'IssuesEvent',
        'pull_request': 'PullRequestEvent',
        'star': 'WatchEvent',  # GitHub API 中 Star 事件实际上是 WatchEvent
        'fork': 'ForkEvent',
        'create': 'CreateEvent',
        'delete': 'DeleteEvent',
        'public': 'PublicEvent',
        'member': 'MemberEvent',
        'commit_comment': 'CommitCommentEvent',
        'issue_comment': 'IssueCommentEvent'
    }

    def __init__(self, config: AstrBotConfig):
        self.config = config

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)

    def update_config(self, key: str, value: Any):
        """更新配置项"""
        self.config.update({key: value})

    def get_monitored_users(self) -> List[str]:
        """获取监控的用户列表"""
        return self.config.get("monitored_users", [])

    def get_target_sessions(self) -> List[str]:
        """获取目标会话列表"""
        return self.config.get("target_sessions", [])

    def get_check_interval(self) -> int:
        """获取检查间隔时间"""
        return self.config.get("check_interval", 300)

    def get_github_token(self) -> str:
        """获取GitHub Token"""
        return self.config.get("github_token", "")

    def get_event_limit(self) -> int:
        """获取事件限制数量"""
        return self.config.get("notification_event_limit", 5)

    def is_image_notification_enabled(self) -> bool:
        """是否启用图片通知"""
        return self.config.get("enable_image_notification", True)

    def get_custom_templates(self) -> Dict[str, Any]:
        """获取自定义模板配置"""
        custom_templates = {}
        for key, value in self.config.items():
            if key.startswith('monitor_') and isinstance(value, dict) and value.get('enabled'):
                event_type = self._convert_monitor_to_event_type(key[8:])  # 移除 "monitor_" 前缀
                custom_templates[event_type] = {k: v for k, v in value.items() if k != 'enabled'}
        return custom_templates

    def _convert_monitor_to_event_type(self, event_type: str) -> str:
        """
        将monitor_配置键转换为事件类型
        例如: monitor_push -> PushEvent
        """
        return self.EVENT_TYPE_MAPPING.get(event_type, event_type.capitalize() + 'Event') 