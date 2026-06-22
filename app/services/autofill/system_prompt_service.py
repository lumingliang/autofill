"""
系统提示词服务
提供系统提示词的CRUD操作
"""
from typing import Any, Dict, List, Optional

from app.log import logger
from app.models.system_prompt import SystemPrompt
from app.repositories.autofill.system_prompt_repository import system_prompt_repository


class SystemPromptService:
    """系统提示词服务"""

    async def create_prompt(
        self,
        name: str,
        content: str,
        description: str = "",
        category: str = "general",
        is_default: bool = False,
        is_active: bool = True
    ) -> SystemPrompt:
        """
        创建系统提示词

        Args:
            name: 提示词名称
            content: 提示词内容
            description: 描述
            category: 分类
            is_default: 是否为默认
            is_active: 是否启用

        Returns:
            创建的SystemPrompt对象
        """
        # 检查是否已存在（Repository 自动应用租户过滤）
        exists = await system_prompt_repository.check_name_exists(name)
        if exists:
            raise ValueError(f"提示词名称 '{name}' 已存在")

        # 如果设置为默认，取消其他默认提示词
        if is_default:
            await system_prompt_repository.clear_default_in_category(category)

        create_data = {
            "name": name,
            "content": content,
            "description": description,
            "category": category,
            "is_default": is_default,
            "is_active": is_active
        }

        prompt = await system_prompt_repository.create(create_data)
        logger.info(f"创建系统提示词: id={prompt.id}, name={name}")
        return prompt

    async def update_prompt(
        self,
        prompt_id: int,
        **kwargs
    ) -> SystemPrompt:
        """
        更新系统提示词

        Args:
            prompt_id: 提示词ID
            **kwargs: 要更新的字段

        Returns:
            更新后的SystemPrompt对象
        """
        # 获取提示词（Repository 自动应用租户过滤）
        prompt = await system_prompt_repository.get_by_id(prompt_id)
        if not prompt:
            raise ValueError(f"提示词不存在或无权访问")

        # 如果更新名称，检查是否重复
        if "name" in kwargs and kwargs["name"] != prompt.name:
            exists = await system_prompt_repository.check_name_exists(
                name=kwargs["name"],
                exclude_id=prompt_id
            )
            if exists:
                raise ValueError(f"提示词名称 '{kwargs['name']}' 已存在")

        # 如果设置为默认，取消其他默认提示词
        if kwargs.get("is_default") and not prompt.is_default:
            category = kwargs.get("category", prompt.category)
            await system_prompt_repository.clear_default_in_category(category)

        # 更新字段
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        prompt = await system_prompt_repository.update(prompt_id, update_data)

        logger.info(f"更新系统提示词: id={prompt_id}")
        return prompt

    async def delete_prompt(self, prompt_id: int) -> bool:
        """
        删除系统提示词

        Args:
            prompt_id: 提示词ID

        Returns:
            是否删除成功
        """
        # 获取提示词（Repository 自动应用租户过滤）
        prompt = await system_prompt_repository.get_by_id(prompt_id)
        if not prompt:
            raise ValueError(f"提示词不存在或无权访问")

        await system_prompt_repository.delete(prompt_id)

        logger.info(f"删除系统提示词: id={prompt_id}, tenant_id={prompt.tenant_id}")
        return True

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[SystemPrompt]:
        """
        根据ID获取提示词

        Args:
            prompt_id: 提示词ID

        Returns:
            SystemPrompt对象或None
        """
        return await system_prompt_repository.get_by_id(prompt_id)

    async def get_prompt_by_name(
        self,
        name: str
    ) -> Optional[SystemPrompt]:
        """
        根据名称获取提示词

        Args:
            name: 提示词名称

        Returns:
            SystemPrompt对象或None
        """
        return await system_prompt_repository.get_by_name(name)

    async def get_default_prompt(
        self,
        category: str = "general"
    ) -> Optional[SystemPrompt]:
        """
        获取默认提示词

        Args:
            category: 分类

        Returns:
            SystemPrompt对象或None
        """
        return await system_prompt_repository.get_default_by_category(category)

    async def list_prompts(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        列表查询系统提示词

        Args:
            category: 分类筛选
            keyword: 关键词搜索（名称或描述）
            is_default: 是否默认筛选
            is_active: 是否启用筛选
            page: 页码
            page_size: 每页数量

        Returns:
            包含total和items的字典
        """
        from tortoise.expressions import Q

        q = Q()

        if category:
            q &= Q(category=category)

        if is_default is not None:
            q &= Q(is_default=is_default)

        if is_active is not None:
            q &= Q(is_active=is_active)

        if keyword:
            q &= Q(name__icontains=keyword) | Q(description__icontains=keyword)

        total, prompts = await system_prompt_repository.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-created_at"]
        )

        items = []
        for prompt in prompts:
            items.append(await prompt.to_dict())

        return {
            "total": total,
            "items": items,
            "page": page,
            "page_size": page_size
        }

    async def get_all_categories(self) -> List[str]:
        """
        获取所有分类列表

        Returns:
            分类列表（去重）
        """
        return await system_prompt_repository.get_all_categories()

    async def get_system_prompt_for_execution(
        self,
        system_prompt: Optional[str] = None,
        system_prompt_name: Optional[str] = None,
        category: str = "general",
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        获取用于执行的系统提示词

        优先级：
        1. 直接传入的 system_prompt
        2. 根据 system_prompt_name 查询数据库
        3. 查询默认提示词
        4. 返回空字符串

        Args:
            system_prompt: 直接传入的提示词
            system_prompt_name: 提示词名称
            category: 分类
            variables: 变量字典，用于替换提示词中的占位符

        Returns:
            系统提示词内容（已替换变量）
        """
        # 1. 优先使用传入的 system_prompt
        if system_prompt:
            return self._render_template(system_prompt, variables)

        # 2. 根据 name 查询
        if system_prompt_name:
            prompt = await self.get_prompt_by_name(name=system_prompt_name)
            if prompt:
                return self._render_template(prompt.content, variables)

        # 3. 查询默认提示词
        default_prompt = await self.get_default_prompt(category=category)
        if default_prompt:
            return self._render_template(default_prompt.content, variables)

        # 4. 返回空字符串
        return ""

    def _render_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染模板，替换变量占位符

        Args:
            template: 模板字符串
            variables: 变量字典

        Returns:
            渲染后的字符串
        """
        if not variables:
            return template

        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                if isinstance(value, list):
                    result = result.replace(placeholder, "\n\n".join(str(v) for v in value))
                else:
                    result = result.replace(placeholder, str(value))
        return result


# 服务实例
system_prompt_service = SystemPromptService()
