"""
MCP 服务注册中心

职责：
- 提供 register_mcp() 供各 MCP 模块注册自己的 SSE ASGI 应用工厂
- 在包导入时自动收集所有已注册的 MCP 服务
- 向主应用暴露 get_mcp_apps()，用于自动挂载到 /mcp/<name>

新增 MCP 服务时，只需在对应模块中调用：

    from app.api.mcp import register_mcp

    @register_mcp("service_name")
    def get_sse_app():
        return mcp.sse_app()

主应用即可自动完成挂载，无需再手动修改 create_app()。
"""
from typing import Any, Callable, Dict, Optional, Union

MCPAppFactory = Callable[[], Any]

_mcp_registry: Dict[str, MCPAppFactory] = {}


def register_mcp(
    name: str, factory: Optional[MCPAppFactory] = None
) -> Union[MCPAppFactory, Callable[[MCPAppFactory], MCPAppFactory]]:
    """注册一个 MCP SSE 应用工厂。

    支持两种调用方式：
        - 普通调用：register_mcp("name", factory)
        - 装饰器：@register_mcp("name")

    Args:
        name: MCP 服务名，将决定挂载路径 /mcp/{name}。
        factory: 返回 SSE ASGI 应用的无参工厂函数；装饰器用法下省略。

    Returns:
        原 factory（普通调用），或接收 factory 的装饰器函数。

    Raises:
        ValueError: 同一 name 被重复注册时抛出。
    """

    def _register(f: MCPAppFactory) -> MCPAppFactory:
        if name in _mcp_registry:
            raise ValueError(f"MCP service '{name}' is already registered")
        _mcp_registry[name] = f
        return f

    if factory is not None:
        return _register(factory)
    return _register


def get_mcp_apps() -> Dict[str, MCPAppFactory]:
    """返回所有已注册的 MCP 应用工厂副本。"""
    return _mcp_registry.copy()


# 导入子模块以触发注册；必须放在 registry 定义之后，避免循环导入
from app.api.mcp import form_field  # noqa: E402,F401
from app.api.mcp import rule_engine  # noqa: E402,F401
