"""
列出所有注册的路由
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app import create_app

app = create_app()

print("=" * 80)
print("注册的路由列表")
print("=" * 80)

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = list(route.methods) if route.methods else []
        methods_str = ', '.join([m for m in methods if m != 'HEAD'])
        print(f"{methods_str:20s} {route.path}")

print("=" * 80)

# 查找比亚迪门店相关路由
print("\n比亚迪门店相关路由:")
for route in app.routes:
    if hasattr(route, 'path') and 'byd' in route.path.lower():
        methods = list(route.methods) if hasattr(route, 'methods') and route.methods else []
        methods_str = ', '.join([m for m in methods if m != 'HEAD'])
        print(f"{methods_str:20s} {route.path}")
