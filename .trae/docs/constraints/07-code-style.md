# 代码风格约束

> 本文档包含 Python Import 规范、代码组织等风格约束规则。

---

## 1. Python Import 规范

### 1.1 绝对禁止函数内 Import

> **⚠️ 绝对禁止**: 严禁在函数、方法内部进行 `import` 操作。

```python
# ❌ 绝对禁止
async def refresh_api(self):
    from app import app  # 绝对禁止！

def process_data(data):
    import json  # 绝对禁止！

# ❌ 错误：在方法内部 import
class MyService:
    async def create(self, obj):
        from app.controllers.user import user_controller  # 绝对禁止！

# ❌ 错误：在异常处理中 import
try:
    result = await process()
except Exception as e:
    import traceback  # 绝对禁止！
    traceback.print_exc()
```

```python
# ✅ 正确：所有 import 必须在文件顶部
import json
import traceback
from typing import Dict, List, Optional

from fastapi import FastAPI

from app import app
from app.controllers.user import user_controller
from app.core.crud import CRUDBase


class MyService:
    async def create(self, obj):
        # 直接使用顶部导入的模块
        result = await user_controller.create(obj)
        return result


async def refresh_api(self):
    # 直接使用顶部导入的 app
    for route in app.routes:
        # ...

def process_data(data):
    # 直接使用顶部导入的 json
    return json.loads(data)

try:
    result = await process()
except Exception as e:
    # 直接使用顶部导入的 traceback
    traceback.print_exc()
```

### 1.2 循环导入解决方案

当遇到循环导入问题时，**禁止**使用函数内 import 作为解决方案。应该通过架构层面的依赖注入或参数传递来解决。

```python
# ❌ 错误：使用函数内 import 解决循环导入
class ApiController:
    async def refresh_api(self):
        from app import app  # 禁止！这是架构问题

# ❌ 错误：使用函数内 import 解决循环导入
class StructuredOutputService:
    async def _record_failure(self, method, error):
        from app.controllers.llm_config import llm_config_controller  # 禁止！
        await llm_config_controller.update_method_status(...)
```

```python
# ✅ 正确：通过参数注入解决循环导入
class ApiController:
    async def refresh_api(self, app: FastAPI):  # 通过参数传递
        for route in app.routes:
            # ...

# ✅ 正确：在 init_app.py 中传递 app 对象
async def init_apis(app: FastAPI):
    await api_controller.refresh_api(app)

# ✅ 正确：通过依赖注入解决
class StructuredOutputService:
    def __init__(self, config_controller=None):
        self.config_controller = config_controller

    async def _record_failure(self, method, error):
        if self.config_controller:
            await self.config_controller.update_method_status(...)
```

### 1.3 Import 分组规范

```python
# ✅ 正确：Import 分组顺序
"""
模块文档字符串
"""

# 第1组：Python 标准库
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

# 第2组：第三方库
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from tortoise.expressions import Q

# 第3组：项目内部模块（按层级从低到高）
from app.core.crud import CRUDBase
from app.core.exceptions import BusinessException
from app.log import logger
from app.models.admin import User
from app.schemas.users import UserCreate, UserUpdate
from app.services.user.user_service import UserService


# 类或函数定义
class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    ...
```

### 1.4 相对 Import 规范

```python
# ✅ 正确：使用绝对导入
from app.services.agent.base.types import APIResult
from app.services.agent.base.exceptions import AgentError

# ❌ 错误：过多层级的相对导入
from ..base.types import APIResult
from ..base.exceptions import AgentError
from ...core.crud import CRUDBase  # 超过两层相对导入禁止
```

### 1.5 Type Checking Only Import

对于仅用于类型注解的导入，使用 `TYPE_CHECKING` 标记：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.admin import User  # 仅在类型检查时使用
    from app.services.llm.llm_config import LLMConfig


class UserService:
    async def get_user(self, user_id: int) -> "User":  # 使用字符串前向引用
        ...
```

---

## 2. 架构分层 Import 约束

```
┌─────────────────────────────────────────────────────────────┐
│                    架构分层 Import 约束                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  api/ (API 层)                                              │
│  ├── 可以导入：controllers/, services/, core/, models/      │
│  └── 禁止导入：无                                           │
│                                                             │
│  controllers/ (控制器层)                                     │
│  ├── 可以导入：models/, schemas/, core/, services/          │
│  └── 禁止导入：api/ (上层), app/__init__.py (循环)          │
│                                                             │
│  services/ (服务层)                                          │
│  ├── 可以导入：models/, core/, controllers/ (谨慎)          │
│  └── 禁止导入：api/ (上层), app/__init__.py (循环)          │
│                                                             │
│  models/ (模型层)                                            │
│  ├── 可以导入：core/ (基础类)                               │
│  └── 禁止导入：api/, controllers/, services/ (上层)         │
│                                                             │
│  core/ (核心层)                                              │
│  ├── 可以导入：settings/, log/                              │
│  └── 禁止导入：api/, controllers/, services/, models/       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 代码组织规范

### 3.1 文件结构

```python
"""
模块文档字符串
"""

# 1. 导入（按分组顺序）
# 2. 常量定义
# 3. 类型定义
# 4. 类定义
# 5. 函数定义
# 6. 模块级代码（如单例实例化）
```

### 3.2 类结构

```python
class MyClass:
    """类文档字符串"""
    
    # 1. 类变量
    CLASS_VAR = "value"
    
    # 2. __init__
    def __init__(self):
        self.instance_var = None
    
    # 3. 属性（@property）
    @property
    def computed_property(self):
        return self.instance_var
    
    # 4. 公有方法
    def public_method(self):
        pass
    
    # 5. 私有方法
    def _private_method(self):
        pass
    
    # 6. 静态方法
    @staticmethod
    def static_method():
        pass
    
    # 7. 类方法
    @classmethod
    def class_method(cls):
        pass
```

---

## 4. 检查清单

在提交代码前，必须检查：

- [ ] 所有 import 都在文件顶部
- [ ] 没有在函数/方法内部的 import
- [ ] 没有在异常处理块中的 import
- [ ] 没有使用函数内 import 解决循环导入
- [ ] import 分组正确（标准库 → 第三方 → 项目内部）
- [ ] 相对导入不超过两层
- [ ] 下层模块没有导入上层模块

---

## 5. 禁止事项清单

- ❌ 禁止在函数/方法内部 import
- ❌ 禁止在异常处理块中 import
- ❌ 禁止使用函数内 import 解决循环导入
- ❌ 禁止超过两层的相对导入
- ❌ 禁止下层模块导入上层模块

---

*详细内容请查看 [tech-constraints-core.md](../tech-constraints-core.md)*
*最后更新: 2026-05-05*
