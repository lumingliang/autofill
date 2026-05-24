"""
系统提示词服务
提供系统提示词的CRUD操作
"""
from typing import Any, Dict, List, Optional

from app.core.tenant import TenantContext
from app.log import logger
from app.models.system_prompt import SystemPrompt


class SystemPromptService:
    """系统提示词服务"""

    async def create_prompt(
        self,
        name: str,
        content: str,
        tenant_id: int,
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
            tenant_id: 租户ID
            description: 描述
            category: 分类
            is_default: 是否为默认
            is_active: 是否启用

        Returns:
            创建的SystemPrompt对象
        """
        # 检查是否已存在
        exists = await SystemPrompt.filter(name=name, tenant_id=tenant_id).exists()
        if exists:
            raise ValueError(f"提示词名称 '{name}' 已存在")

        # 如果设置为默认，取消其他默认提示词
        if is_default:
            await SystemPrompt.filter(
                tenant_id=tenant_id,
                category=category,
                is_default=True
            ).update(is_default=False)

        prompt = await SystemPrompt.create(
            name=name,
            content=content,
            tenant_id=tenant_id,
            description=description,
            category=category,
            is_default=is_default,
            is_active=is_active
        )

        logger.info(f"创建系统提示词: id={prompt.id}, name={name}, tenant_id={tenant_id}")
        return prompt

    async def update_prompt(
        self,
        prompt_id: int,
        tenant_id: int,
        **kwargs
    ) -> SystemPrompt:
        """
        更新系统提示词

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID（用于权限验证）
            **kwargs: 要更新的字段

        Returns:
            更新后的SystemPrompt对象
        """
        prompt = await SystemPrompt.filter(id=prompt_id, tenant_id=tenant_id).first()
        if not prompt:
            raise ValueError(f"提示词不存在或无权访问")

        # 如果更新名称，检查是否重复
        if "name" in kwargs and kwargs["name"] != prompt.name:
            exists = await SystemPrompt.filter(
                name=kwargs["name"],
                tenant_id=tenant_id
            ).exclude(id=prompt_id).exists()
            if exists:
                raise ValueError(f"提示词名称 '{kwargs['name']}' 已存在")

        # 如果设置为默认，取消其他默认提示词
        if kwargs.get("is_default") and not prompt.is_default:
            category = kwargs.get("category", prompt.category)
            await SystemPrompt.filter(
                tenant_id=tenant_id,
                category=category,
                is_default=True
            ).update(is_default=False)

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)

        await prompt.save()

        logger.info(f"更新系统提示词: id={prompt_id}, tenant_id={tenant_id}")
        return prompt

    async def delete_prompt(self, prompt_id: int, tenant_id: int, is_superuser: bool = False) -> bool:
        """
        删除系统提示词

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID（用于权限验证）
            is_superuser: 是否为超级管理员

        Returns:
            是否删除成功
        """
        # 超管可以删除任何提示词（包括全局），普通用户只能删除自己租户的
        if is_superuser:
            # 超管：如果指定了租户ID，则按租户ID查询；否则直接按ID查询
            if tenant_id > 0:
                prompt = await SystemPrompt.filter(id=prompt_id, tenant_id=tenant_id).first()
            else:
                prompt = await SystemPrompt.filter(id=prompt_id).first()
        else:
            # 普通用户：只能删除自己租户的提示词
            prompt = await SystemPrompt.filter(id=prompt_id, tenant_id=tenant_id).first()

        if not prompt:
            raise ValueError(f"提示词不存在或无权访问")

        # 普通用户不能删除全局默认提示词
        if not is_superuser and prompt.tenant_id == 0:
            raise ValueError("全局默认提示词不允许删除")

        await prompt.delete()

        logger.info(f"删除系统提示词: id={prompt_id}, tenant_id={prompt.tenant_id}, is_superuser={is_superuser}")
        return True

    async def get_prompt_by_id(self, prompt_id: int, tenant_id: int, is_superuser: bool = False) -> Optional[SystemPrompt]:
        """
        根据ID获取提示词

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID（用于权限验证）
            is_superuser: 是否为超级管理员

        Returns:
            SystemPrompt对象或None
        """
        # 超管无租户限制，可以直接查询
        if is_superuser:
            return await SystemPrompt.filter(id=prompt_id).first()
        # 普通用户只能查询自己租户的提示词
        return await SystemPrompt.filter(id=prompt_id, tenant_id=tenant_id).first()

    async def get_prompt_by_name(
        self,
        name: str,
        tenant_id: int
    ) -> Optional[SystemPrompt]:
        """
        根据名称获取提示词

        Args:
            name: 提示词名称
            tenant_id: 租户ID

        Returns:
            SystemPrompt对象或None
        """
        return await SystemPrompt.filter(
            name=name,
            tenant_id=tenant_id,
            is_active=True
        ).first()

    async def get_default_prompt(
        self,
        tenant_id: int,
        category: str = "general"
    ) -> Optional[SystemPrompt]:
        """
        获取默认提示词

        Args:
            tenant_id: 租户ID
            category: 分类

        Returns:
            SystemPrompt对象或None
        """
        # 先查询租户级别的默认提示词
        prompt = await SystemPrompt.filter(
            tenant_id=tenant_id,
            category=category,
            is_default=True,
            is_active=True
        ).first()

        # 如果没有，查询全局默认
        if not prompt:
            prompt = await SystemPrompt.filter(
                tenant_id=0,
                category=category,
                is_default=True,
                is_active=True
            ).first()

        return prompt

    async def list_prompts(
        self,
        tenant_id: int,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        is_default: Optional[bool] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        is_superuser: bool = False
    ) -> Dict[str, Any]:
        """
        列表查询系统提示词

        Args:
            tenant_id: 租户ID
            category: 分类筛选
            keyword: 关键词搜索（名称或描述）
            is_default: 是否默认筛选
            is_active: 是否启用筛选
            page: 页码
            page_size: 每页数量
            is_superuser: 是否为超级管理员

        Returns:
            包含total和items的字典
        """
        # 超管不传租户ID时（tenant_id=0），查询所有数据
        # 超管传了租户ID时，只查询该租户的数据
        # 普通用户只能查询自己租户的数据 + 全局数据
        if is_superuser:
            if tenant_id == 0:
                # 超管无租户限制，查询所有
                query = SystemPrompt.filter()
            else:
                # 超管指定了租户ID，只查询该租户的数据
                query = SystemPrompt.filter(tenant_id=tenant_id)
        else:
            # 普通用户，查询自己租户 + 全局提示词(tenant_id=0)
            query = SystemPrompt.filter(tenant_id__in=[tenant_id, 0])

        if category:
            query = query.filter(category=category)

        if is_default is not None:
            query = query.filter(is_default=is_default)

        if is_active is not None:
            query = query.filter(is_active=is_active)

        if keyword:
            query = query.filter(
                name__icontains=keyword
            ) | query.filter(
                description__icontains=keyword
            )

        total = await query.count()

        prompts = await query.order_by("-created_at").offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        items = []
        for prompt in prompts:
            items.append(await prompt.to_dict())

        return {
            "total": total,
            "items": items,
            "page": page,
            "page_size": page_size
        }

    async def get_all_categories(self, tenant_id: int, is_superuser: bool = False) -> List[str]:
        """
        获取所有分类列表

        Args:
            tenant_id: 租户ID
            is_superuser: 是否为超级管理员

        Returns:
            分类列表（去重）
        """
        # 超管不传租户ID时，查询所有分类
        # 超管传了租户ID时，只查询该租户的分类
        # 普通用户，查询自己租户 + 全局的分类
        if is_superuser:
            if tenant_id == 0:
                prompts = await SystemPrompt.filter().distinct().values_list("category", flat=True)
            else:
                prompts = await SystemPrompt.filter(
                    tenant_id=tenant_id
                ).distinct().values_list("category", flat=True)
        else:
            prompts = await SystemPrompt.filter(
                tenant_id__in=[tenant_id, 0]
            ).distinct().values_list("category", flat=True)

        # 去重并过滤空值
        categories = list(set([c for c in prompts if c]))
        categories.sort()

        return categories

    async def get_system_prompt_for_execution(
        self,
        tenant_id: int,
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
        4. 从JSON配置文件读取
        5. 返回空字符串

        Args:
            tenant_id: 租户ID
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
            prompt = await self.get_prompt_by_name(
                name=system_prompt_name,
                tenant_id=tenant_id
            )
            if prompt:
                return self._render_template(prompt.content, variables)

            # 如果没找到，尝试查询全局
            prompt = await self.get_prompt_by_name(
                name=system_prompt_name,
                tenant_id=0
            )
            if prompt:
                return self._render_template(prompt.content, variables)

        # 3. 查询默认提示词
        default_prompt = await self.get_default_prompt(
            tenant_id=tenant_id,
            category=category
        )
        if default_prompt:
            return self._render_template(default_prompt.content, variables)

        # 4. 从JSON配置文件读取默认提示词
        default_prompt_content = self._get_default_prompt_from_config(category)
        if default_prompt_content:
            return self._render_template(default_prompt_content, variables)

        # 5. 返回空字符串
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

    def _get_default_prompt_from_config(self, category: str) -> str:
        """
        从JSON配置文件读取默认提示词

        Args:
            category: 分类

        Returns:
            提示词内容或空字符串
        """
        try:
            import json
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "config" / "system_prompts.json"
            if not config_path.exists():
                return ""

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            for prompt_data in config.get("prompts", []):
                if prompt_data.get("category") == category and prompt_data.get("is_default", False):
                    return prompt_data.get("content", "")

            return ""
        except Exception:
            return ""


# 服务实例
system_prompt_service = SystemPromptService()
