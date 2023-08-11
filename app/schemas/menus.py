from enum import StrEnum

from pydantic import BaseModel, Field


class MenuType(StrEnum):
    CATALOG = "catalog"  # 目录
    MENU = "menu"  # 菜单


class BaseMenu(BaseModel):
    id: int
    name: str = ""
    path: str = ""
    remark: dict = {}
    menu_type: MenuType = MenuType.CATALOG
    icon: str = ""
    order: int = 0
    parent_id: int = 0
    is_hidden: bool = False
    component: str = ""
    keepalive: bool = True
    redirect: str = ""
    children: list["BaseMenu"] = []


class MenuCreate(BaseModel):
    menu_type: MenuType = Field(default=MenuType.CATALOG.value)
    name: str = Field(example="用户管理")
    icon: str = Field(default="ph:user-list-bold")
    path: str = Field(example="/system/user")
    order: int = Field(default=0, example=1)
    parent_id: int = Field(default=0, example=0)
    is_hidden: bool = Field(default=False)
    component: str = Field(default="Layout", example="/system/user")
    keepalive: bool = Field(default=True)
    redirect: str = Field(default="")


class MenuUpdate(BaseModel):
    id: int
    menu_type: MenuType = Field(default=MenuType.CATALOG)
    name: str = Field(example="用户管理")
    icon: str = Field(default="ph:user-list-bold")
    path: str = Field(example="/system/user")
    order: int = Field(default=0, example=1)
    parent_id: int = Field(default=0, example=0)
    is_hidden: bool = Field(default=False)
    component: str = Field(example="/system/user")
    keepalive: bool = Field(default=False)
    redirect: str = Field(default="")
