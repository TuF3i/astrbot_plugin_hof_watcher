# API 接口文档

## 通用约定

### 响应格式

所有接口返回 HTTP 200，业务状态码在 body 的 `code` 字段：

```json
{
  "code": 10200,
  "msg": "Operation Success",
  "data": null
}
```

### 错误码

| code | 含义 |
|------|------|
| 10200 | 成功 |
| 40000 | 请求参数错误 |
| 40100 | 未认证 |
| 40300 | 无权限 |
| 40400 | 资源不存在 |
| 40900 | 资源冲突 |
| 50000 | 服务器内部错误 |

### 分页

分页参数统一为 `?page=1&page_size=20`，page 从 1 开始。

分页响应格式：

```json
{
  "code": 10200,
  "msg": "Operation Success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

---

## Web API (端口 8080)

### 认证接口 — 无需鉴权

#### POST /api/auth/register

注册新用户。

**请求：**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "nickname"
}
```

**响应：**
```json
{
  "code": 10200,
  "data": {
    "uid": "uuid-string",
    "email": "user@example.com",
    "nickname": "nickname",
    "access_token": "jwt-access-token",
    "refresh_token": "jwt-refresh-token"
  }
}
```

#### POST /api/auth/login

登录。

**请求：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应（成功）：**
```json
{
  "code": 10200,
  "data": {
    "access_token": "jwt-access-token",
    "refresh_token": "jwt-refresh-token",
    "user": {
      "uid": "uuid",
      "email": "user@example.com",
      "nickname": "nickname",
      "role": "user"
    }
  }
}
```

**错误：**
- `code: 40300` — 账号被 ban
- `code: 40100` — 邮箱或密码错误

#### POST /api/auth/refresh

刷新 JWT Token。

**请求：**
```json
{
  "refresh_token": "jwt-refresh-token"
}
```

**响应：**
```json
{
  "code": 10200,
  "data": {
    "access_token": "new-jwt-access-token",
    "refresh_token": "new-jwt-refresh-token"
  }
}
```

### 金句接口 — 需 JWT 认证

#### GET /api/quotes/speakers

获取发言者列表。

**参数：** `?page=1&page_size=20`

**响应：**
```json
{
  "code": 10200,
  "data": {
    "items": [
      {
        "qqnumber": "123456",
        "speaker": "昵称",
        "avatar": "url",
        "quote_count": 42
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

#### GET /api/quotes/speakers/:qqNumber/quotes

获取某个发言者的发言。

**参数：** `?page=1&page_size=20`

**响应：**
```json
{
  "code": 10200,
  "data": {
    "items": [
      {
        "qid": "uuid",
        "content": "消息内容",
        "suppression": 85,
        "userdata": {
          "qqnumber": "123456",
          "speaker": "昵称",
          "avatar": "url"
        },
        "groupdata": {
          "groupnumber": "群号",
          "groupname": "群名",
          "avatar": "url"
        },
        "attachmentid": ["att-uuid"],
        "is_featured": false
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### GET /api/quotes/featured

获取所有精华发言。

**参数：** `?page=1&page_size=20`

#### GET /api/quotes/attachments/:qid/:attId

获取附件图片。直接返回图片二进制（Content-Type: image/jpeg）。

### 管理接口 — 需 JWT + Admin 权限

#### GET /api/admin/users

获取用户列表。

**参数：** `?page=1&page_size=20`

**响应：**
```json
{
  "code": 10200,
  "data": {
    "items": [
      {
        "uid": "uuid",
        "email": "user@example.com",
        "nickname": "nickname",
        "role": "user"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

#### PUT /api/admin/users/:uid/role

修改用户角色。

**请求：**
```json
{
  "role": "admin"
}
```

可选值：`admin`, `user`, `banned`。改为 `banned` 时自动清除该用户的 Redis Token。

#### DELETE /api/admin/users/:uid

删除用户。

#### POST /api/admin/quotes/trigger

手动触发 AI 分析。立即弹出 Redis 队列全部消息 → 调用 LLM 分析 → 高性压抑度发言写入 MongoDB。异步执行，不阻塞调用方。

#### GET /api/admin/quotes

获取所有发言。

**参数：** `?page=1&page_size=20`

#### POST /api/admin/quotes

新建发言（multipart/form-data）。

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| content | string | 是 | 发言内容 |
| userdata | string | 是 | JSON: `{"qqnumber":"...","speaker":"...","avatar":"..."}` |
| groupdata | string | 否 | JSON: `{"groupnumber":"...","groupname":"...","avatar":"..."}` |
| suppression | float | 否 | 压抑值，默认 0 |
| files | file[] | 否 | 附件图片 |

#### PUT /api/admin/quotes/:qid/featured

设置/取消精华。

**请求：**
```json
{
  "featured": true
}
```

#### DELETE /api/admin/quotes/:qid

删除发言（同时删除 MinIO 中的附件）。

#### DELETE /api/admin/speakers/:qqNumber

删除发言者及其所有发言（同时删除所有附件）。

---

## Bot API (端口 9090)

无需鉴权，用于 QQ 机器人插件采集消息。

#### POST /api/bot/upload

上传消息到 Redis 队列。使用 multipart/form-data 编码。

**请求（multipart/form-data）：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| qqgroup | string | 是 | 群号 |
| qqnumber | string | 是 | 发言者 QQ 号 |
| speaker | string | 是 | 发言者昵称 |
| content | string | 是 | 消息内容 |
| avatar | string | 否 | 用户头像 URL |
| groupname | string | 否 | 群名称 |
| groupavatar | string | 否 | 群头像 URL |
| files | file[] | 否 | 附件图片 |

**响应：**
```json
{
  "code": 10200,
  "msg": "ok",
  "data": null
}
```

消息进入 Redis List `bot:message_queue`，由后台 Consumer 协程每 10 秒检查队列长度，积压到 300 条或每天午夜 00:00 时发送给 LLM 分析，提取 0-15 条高性压抑值的发言写入 MongoDB。

#### POST /api/bot/import

直接写入数据库（不进 Redis 缓冲区），用于已筛选发言即时入库。

**请求（multipart/form-data）：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| qqgroup | string | 是 | 群号 |
| qqnumber | string | 是 | 发言者 QQ 号 |
| speaker | string | 是 | 发言者昵称 |
| content | string | 是 | 消息内容 |
| avatar | string | 否 | 用户头像 URL |
| groupname | string | 否 | 群名称 |
| groupavatar | string | 否 | 群头像 URL |
| files | file[] | 否 | 附件图片 |

**响应：**
```json
{
  "code": 10200,
  "data": {
    "qid": "uuid",
    "content": "消息内容",
    "suppression": 0,
    "userdata": {
      "qqnumber": "123456",
      "speaker": "昵称",
      "avatar": "url"
    },
    "groupdata": {
      "groupnumber": "群号",
      "groupname": "群名",
      "avatar": "url"
    },
    "attachmentid": [],
    "is_featured": false
  }
}
```
