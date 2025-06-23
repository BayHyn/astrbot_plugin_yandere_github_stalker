# GitHub User Activity Monitor Plugin

这是一个用于监控 GitHub 用户活动的 AstrBot 插件。它可以实时追踪指定用户的 GitHub 活动，并通过图片或文本的形式发送通知。

## 功能特点

- 实时监控多个 GitHub 用户的活动
- 支持多种活动类型的识别和展示
- 提供精美的图片通知和简洁的文本通知
- 可配置的检查间隔和通知方式
- 支持 GitHub API Token 以提高 API 访问限制

## 安装

1. 将插件目录复制到 AstrBot 的 plugins 目录下
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 安装 Playwright：
   ```bash
   playwright install chromium
   ```

## 配置

在 AstrBot 的配置文件中添加以下配置：

```json
{
    "target_users": ["用户名1", "用户名2"],
    "target_sessions": ["会话ID1", "会话ID2"],
    "check_interval": 300,
    "github_token": "your_github_token",
    "enable_startup_notification": true,
    "enable_image_notification": true
}
```

## 可用命令

- `stalker_status`: 查看当前监控的用户状态
- `stalker_test`: 测试通知功能
- `stalker_force_check`: 强制检查所有用户的活动

## 通知示例

### 文本通知
```
👤 GitHub用户 @username 有新活动！

📌 PushEvent
📁 owner/repo
📝 推送了 3 个提交
🕒 2024-01-01 12:34:56
```

### 图片通知
- 精美的图片通知，包含用户头像和详细活动信息
- 支持多种活动类型的可视化展示
- 美观的布局和动画效果

## 注意事项

1. 建议配置 GitHub Token 以获得更高的 API 访问限制
2. 合理设置检查间隔，避免触发 GitHub API 限制
3. 图片通知需要安装 Playwright 和 Chromium

## License

MIT License
