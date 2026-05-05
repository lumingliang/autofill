# 日志记录约束

> 本文档包含日志记录的所有约束规则。

---

## 1. 日志框架使用规范

> **⚠️ 重要约束**: 项目使用 loguru 作为核心日志框架，通过自定义代理类兼容标准库 logging。

### 1.1 使用项目统一日志模块

```python
# ✅ 正确：使用项目统一的日志模块
from app.log import getLogger

logger = getLogger(__name__)
logger.info("用户登录成功", user_id=user.id)
logger.error("数据库连接失败", error=str(e))

# ✅ 正确：使用 bind 添加上下文
logger.bind(request_id=request_id, user_id=user_id).info("处理请求")

# ❌ 错误：直接使用标准库 logging
import logging
logger = logging.getLogger(__name__)  # 不允许

# ❌ 错误：直接使用 loguru
from loguru import logger  # 不允许，使用项目封装的模块
```

---

## 2. 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| DEBUG | 开发调试信息，生产环境关闭 | `logger.debug(f"SQL: {sql}")` |
| INFO | 业务流程记录 | `logger.info("用户创建成功", user_id=123)` |
| WARNING | 非致命异常，可恢复错误 | `logger.warning("请求限流", client_ip=ip)` |
| ERROR | 业务错误，需要处理 | `logger.error("数据库查询失败", error=str(e))` |
| CRITICAL | 系统级错误，需要立即处理 | `logger.critical("服务启动失败")` |

---

## 3. 日志内容规范

### 3.1 结构化日志

```python
# ✅ 正确：结构化日志，使用关键字参数
logger.info(
    "订单处理完成",
    order_id=order.id,
    user_id=order.user_id,
    amount=order.amount,
    duration_ms=processing_time
)

# ✅ 正确：异常日志包含完整上下文
try:
    result = await process_data()
except Exception as e:
    logger.error(
        "数据处理失败",
        error=str(e),
        error_type=type(e).__name__,
        data_id=data.id,
        retry_count=retry
    )

# ❌ 错误：使用字符串拼接
logger.info("用户" + user.name + "登录成功")  # 不允许

# ❌ 错误：敏感信息未脱敏
logger.info("用户登录", password=password)  # 不允许！
```

### 3.2 日志脱敏规范

```python
# ✅ 正确：敏感字段自动脱敏
SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "authorization"}

# 在日志中自动过滤
logger.bind(
    username=user.username,
    password="***",  # 脱敏显示
    token="***"      # 脱敏显示
).info("用户信息")

# ❌ 错误：明文记录敏感信息
logger.info("用户登录", password=raw_password, token=access_token)
```

---

## 4. 请求日志规范

> **⚠️ 重要约束**: 所有 HTTP 请求必须通过 `RequestLoggingMiddleware` 自动记录，禁止在业务代码中重复记录请求日志。

### 4.1 自动记录的字段

```python
{
    "timestamp": "2026-05-02T14:42:56.330878+08:00",
    "level": "INFO",
    "message": "POST /api/v1/base/access_token - 422",
    "method": "POST",
    "path": "/api/v1/base/access_token",
    "query": "",
    "status_code": 422,
    "duration_ms": 3.2,
    "client_ip": "127.0.0.1",
    "request_params": {"invalid": "data"},
    "request_id": "d5329543-0178-456e-b8f8-d62804fc9289"
}
```

### 4.2 禁止重复记录

```python
# ❌ 错误：在业务代码中重复记录请求日志
@router.post("/login")
async def login(data: LoginData):
    logger.info(f"用户登录请求: {data.username}")  # 不需要，中间件已记录
    ...
```

---

## 5. 异常日志规范

> **⚠️ 重要约束**: 所有异常必须通过全局异常处理器捕获并记录，禁止在业务代码中捕获异常后仅打印日志而不处理。

### 5.1 让异常冒泡到全局处理器

```python
# ✅ 正确：让异常冒泡到全局处理器
@router.post("/process")
async def process(data: ProcessData):
    # 不做 try-except，让异常被全局处理器捕获
    result = await service.process(data)
    return Success(data=result)

# ✅ 正确：需要特定处理时，重新抛出
@router.post("/transfer")
async def transfer(data: TransferData):
    try:
        await service.transfer(data)
    except InsufficientBalanceException:
        # 转换为业务异常，会被记录
        raise BusinessException(code=400, msg="余额不足")
```

### 5.2 禁止吞掉异常

```python
# ❌ 错误：捕获异常仅打印日志
@router.post("/process")
async def process(data: ProcessData):
    try:
        result = await service.process(data)
    except Exception as e:
        logger.error(f"处理失败: {e}")  # 不允许！异常被吞掉了
        return Fail(msg="处理失败")  # 没有 request_id，没有调用栈
```

---

## 6. 配置约束

### 6.1 环境配置

```python
# settings/config.py
class Settings(BaseSettings):
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json 或 text
```

---

## 7. 禁止事项清单

- ❌ 禁止直接使用标准库 logging
- ❌ 禁止直接使用 loguru
- ❌ 禁止在业务代码中重复记录请求日志
- ❌ 禁止捕获异常仅打印日志而不处理（吞掉异常）
- ❌ 禁止明文记录敏感信息（password、token 等）
- ❌ 禁止使用字符串拼接日志内容

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
