from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.core.crud import CRUDBase
from app.models.admin import Dept, DeptClosure, Tenant
from app.schemas.depts import DeptCreate, DeptUpdate
from app.settings.config import settings


class DeptController(CRUDBase[Dept, DeptCreate, DeptUpdate]):
    def __init__(self):
        super().__init__(model=Dept)

    async def get_dept_tree(self, name):
        q = Q()
        # 获取所有未被软删除的部门
        q &= Q(is_deleted=False)
        if name:
            q &= Q(name__contains=name)
        return await self.get_dept_tree_with_query(q)

    async def get_dept_tree_with_query(self, q: Q, include_tenant: bool = False):
        """根据查询条件获取部门树
        
        Args:
            q: 查询条件
            include_tenant: 是否包含租户名称（仅超级管理员使用）
        """
        all_depts = await self.model.filter(q).order_by("order")
        
        # 如果需要包含租户信息，预加载租户数据
        tenant_map = {}
        if include_tenant:
            tenant_ids = [dept.tenant_id for dept in all_depts if dept.tenant_id]
            if tenant_ids:
                tenants = await Tenant.filter(id__in=tenant_ids)
                tenant_map = {t.id: t for t in tenants}

        # 辅助函数，用于递归构建部门树
        def build_tree(parent_id):
            result = []
            for dept in all_depts:
                if dept.parent_id == parent_id:
                    node = {
                        "id": dept.id,
                        "name": dept.name,
                        "desc": dept.desc,
                        "order": dept.order,
                        "parent_id": dept.parent_id,
                        "children": build_tree(dept.id),  # 递归构建子部门
                    }
                    # 添加租户名称
                    if include_tenant and dept.tenant_id and dept.tenant_id in tenant_map:
                        node["tenant_name"] = tenant_map[dept.tenant_id].name
                    result.append(node)
            return result

        # 从顶级部门（parent_id=0）开始构建部门树
        dept_tree = build_tree(0)
        return dept_tree

    async def get_dept_info(self):
        pass

    async def update_dept_closure(self, obj: Dept):
        parent_depts = await DeptClosure.filter(descendant=obj.parent_id)
        for i in parent_depts:
            print(i.ancestor, i.descendant)
        dept_closure_objs: list[DeptClosure] = []
        # 插入父级关系
        for item in parent_depts:
            dept_closure_objs.append(DeptClosure(ancestor=item.ancestor, descendant=obj.id, level=item.level + 1))
        # 插入自身x
        dept_closure_objs.append(DeptClosure(ancestor=obj.id, descendant=obj.id, level=0))
        # 创建关系
        await DeptClosure.bulk_create(dept_closure_objs)

    @atomic(connection_name="mysql")
    async def create_dept(self, obj_in: DeptCreate):
        # 创建
        if obj_in.parent_id != 0:
            await self.get(id=obj_in.parent_id)
        new_obj = await self.create(obj_in=obj_in)
        await self.update_dept_closure(new_obj)

    @atomic(connection_name="mysql")
    async def update_dept(self, obj_in: DeptUpdate):
        dept_obj = await self.get(id=obj_in.id)
        # 更新部门关系
        if dept_obj.parent_id != obj_in.parent_id:
            await DeptClosure.filter(ancestor=dept_obj.id).delete()
            await DeptClosure.filter(descendant=dept_obj.id).delete()
            await self.update_dept_closure(dept_obj)
        # 更新部门信息
        dept_obj.update_from_dict(obj_in.model_dump(exclude_unset=True))
        await dept_obj.save()

    @atomic(connection_name="mysql")
    async def delete_dept(self, dept_id: int):
        # 删除部门
        obj = await self.get(id=dept_id)
        obj.is_deleted = True
        await obj.save()
        # 删除关系
        await DeptClosure.filter(descendant=dept_id).delete()


dept_controller = DeptController()
