"""
部门 Service 层

处理部门相关的业务逻辑，包括：
- 获取部门树
- 部门CRUD操作
- 部门闭包关系维护

约束：
- 使用 @atomic 装饰器控制事务
- 不重复判断权限（中间件已完成认证）
- 租户信息从 Ctx 获取
- 不直接查询 Model 层，通过 Repository 层访问数据
"""

from typing import Any, Dict, List

from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.models.admin import Dept
from app.repositories import dept_repository, dept_closure_repository


class DeptService:
    """
    部门 Service

    职责：
    - 处理部门相关的业务逻辑
    - 调用 Repository 层进行数据操作

    约束：
    - 不直接操作数据库，通过 Repository 层访问数据
    - 不处理 HTTP 请求/响应
    """

    async def get_dept_tree(
        self,
        name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        获取部门树

        Args:
            name: 部门名称模糊查询

        Returns:
            List[Dict[str, Any]]: 部门树结构
        """
        # 构建查询条件（不包含租户过滤，由 Repository 层自动处理）
        q = Q(is_deleted=False)
        if name:
            q &= Q(name__contains=name)

        # Repository 层自动应用租户过滤（通过 Ctx.get_effective_tenant_id()）
        depts = await dept_repository.filter(q).order_by("order").all()

        return await self._build_dept_tree(depts)

    async def get_by_id(self, dept_id: int) -> Dict[str, Any]:
        """
        根据ID获取部门

        Args:
            dept_id: 部门ID

        Returns:
            Dict[str, Any]: 部门字典
        """
        dept = await dept_repository.get_by_id(dept_id)
        return await dept.to_dict()

    @atomic()
    async def create(self, dept_in: Dict[str, Any]) -> None:
        """
        创建部门

        Args:
            dept_in: 部门创建数据
        """
        parent_id = dept_in.get("parent_id", 0)

        # 验证父部门存在
        if parent_id != 0:
            await dept_repository.get_by_id(parent_id)

        # 创建部门
        new_dept = await dept_repository.create(dept_in)

        # 更新闭包关系
        await self._update_dept_closure(new_dept)

    @atomic()
    async def update(self, dept_id: int, dept_in: Dict[str, Any]) -> None:
        """
        更新部门

        Args:
            dept_id: 部门ID
            dept_in: 部门更新数据
        """
        dept_obj = await dept_repository.get_by_id(dept_id)
        new_parent_id = dept_in.get("parent_id", dept_obj.parent_id)

        # 如果父部门变更，更新闭包关系
        if dept_obj.parent_id != new_parent_id:
            # 删除旧的闭包关系
            await dept_closure_repository.filter(ancestor=dept_obj.id).delete()
            await dept_closure_repository.filter(descendant=dept_obj.id).delete()
            # 更新部门信息
            await dept_repository.update(dept_id, dept_in)
            # 重新加载部门对象
            dept_obj = await dept_repository.get_by_id(dept_id)
            # 创建新的闭包关系
            await self._update_dept_closure(dept_obj)
        else:
            # 只更新部门信息
            await dept_repository.update(dept_id, dept_in)

    @atomic()
    async def delete(self, dept_id: int) -> None:
        """
        删除部门（软删除）

        Args:
            dept_id: 部门ID
        """
        dept_obj = await dept_repository.get_by_id(dept_id)
        dept_obj.is_deleted = True
        await dept_obj.save()

        # 删除闭包关系
        await dept_closure_repository.filter(descendant=dept_id).delete()

    async def _update_dept_closure(self, dept: Dept) -> None:
        """
        更新部门闭包关系

        Args:
            dept: 部门对象
        """
        parent_id = dept.parent_id

        if parent_id != 0:
            # 获取父部门的所有祖先
            parent_ancestors = await dept_closure_repository.filter(descendant=parent_id).all()
            for ancestor in parent_ancestors:
                await dept_closure_repository.create({
                    "ancestor": ancestor.ancestor,
                    "descendant": dept.id,
                    "level": ancestor.level + 1
                })

        # 添加自身关系
        await dept_closure_repository.create({
            "ancestor": dept.id,
            "descendant": dept.id,
            "level": 0
        })

    async def _build_dept_tree(
        self,
        depts: List[Dept],
    ) -> List[Dict[str, Any]]:
        """
        构建部门树

        Args:
            depts: 部门列表

        Returns:
            List[Dict[str, Any]]: 部门树结构
        """
        if not depts:
            return []

        # 辅助函数，用于递归构建部门树
        def build_tree(parent_id: int) -> List[Dict[str, Any]]:
            result = []
            for dept in depts:
                if dept.parent_id == parent_id:
                    node = {
                        "id": dept.id,
                        "name": dept.name,
                        "desc": dept.desc,
                        "order": dept.order,
                        "parent_id": dept.parent_id,
                        "children": build_tree(dept.id),
                    }
                    result.append(node)
            return result

        # 从顶级部门（parent_id=0）开始构建部门树
        return build_tree(0)


dept_service = DeptService()
