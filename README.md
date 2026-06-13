# astrbot_plugin_hof_watcher

HallOfFame 消息采集插件 —— 自动采集 QQ 群文本消息并上传至 HallOfFame 后端，支持管理员手动导入带图片的言论。

## 功能

- **自动言论采集**：监听启用的 QQ 群，自动采集纯文本消息，通过 `/api/bot/upload` 静默上传至后端
- **手动导入**：管理员可通过 `/hall add` 指令引用群成员消息，提取文字和图片并导入至后端（`/api/bot/import`）
- **可视化配置**：在 WebUI 中设置后端 API 地址和启用采集的群号列表

## 配置

在 AstrBot WebUI 插件管理页面中配置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `base_url` | string | `http://localhost:9090` | HallOfFame Bot API 地址 |
| `enabled_groups` | list | `[]` | 启用消息采集的群号列表 |

## 指令

### `/hall add`

仅管理员可使用。引用一条群成员的消息后发送该指令，插件将提取被引用消息中的文字和图片，直接导入到 HallOfFame 数据库。

## 依赖

- `aiohttp`

## 后端 API

本插件依赖 HallOfFame 后端提供的 Bot API（默认端口 9090）：

- `POST /api/bot/upload` — 消息上传至 Redis 队列
- `POST /api/bot/import` — 直接导入消息到数据库

详见 [API 文档](docs/api.md)。
