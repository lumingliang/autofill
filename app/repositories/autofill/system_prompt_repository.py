"""
SystemPrompt Repository - 系统提示词数据访问层

严格遵循技术约束文档：
- 继承 BaseRepository 获得通用 CRUD 能力
- 自动应用租户过滤（通过 BaseRepository）
- 禁止手动传递 tenant_id 参数
- 使用 self.filter() 进行链式查询
"""
from typing import List, Optional

from app.models.system_prompt import SystemPrompt
from app.repositories.base_repository import BaseRepository


class SystemPromptRepository(BaseRepository[SystemPrompt]):
    """
    系统提示词 Repository

    职责：
    - 系统提示词相关的数据访问操作
    - 继承 BaseRepository 获得通用 CRUD 能力
    - 自动应用租户过滤

    约束：
    - 禁止直接查询 Model，使用 self.filter() 方法
    - 禁止手动传递 tenant_id 参数，从 Ctx 获取
    """

    def __init__(self):
        super().__init__(SystemPrompt)

    async def get_by_name(self, name: str) -> Optional[SystemPrompt]:
        """
        根据名称获取提示词

        自动应用租户过滤（通过 self.filter）

        Args:
            name: 提示词名称

        Returns:
            SystemPrompt 对象或 None
        """
        return await self.filter(name=name, is_active=True).first()

    async def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查提示词名称是否已存在

        Args:
            name: 提示词名称
            exclude_id: 要排除的提示词ID（用于更新时排除自身）

        Returns:
            是否存在
        """
        query = self.filter(name=name)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def get_default_by_category(self, category: str) -> Optional[SystemPrompt]:
        """
        获取指定分类的默认提示词

        自动应用租户过滤（通过 self.filter）

        Args:
            category: 分类

        Returns:
            SystemPrompt 对象或 None
        """
        return await self.filter(
            category=category,
            is_default=True,
            is_active=True
        ).first()

    async def list_by_category(self, category: str) -> List[SystemPrompt]:
        """
        根据分类获取提示词列表

        自动应用租户过滤（通过 self.filter）

        Args:
            category: 分类

        Returns:
            SystemPrompt 列表
        """
        return await self.filter(category=category).all()

    async def get_all_categories(self) -> List[str]:
        """
        获取所有分类列表

        自动应用租户过滤（通过 self.filter）

        Returns:
            分类列表（去重）
        """
        prompts = await self.filter().distinct().values_list("category", flat=True)
        categories = list(set([c for c in prompts if c]))
        categories.sort()
        return categories

    async def clear_default_in_category(self, category: str) -> None:
        """
        清除指定分类的默认提示词设置

        自动应用租户过滤（通过 self.filter）

        Args:
            category: 分类
        """
        await self.filter(
            category=category,
            is_default=True
        ).update(is_default=False)


# 创建全局仓库实例
system_prompt_repository = SystemPromptRepository()
