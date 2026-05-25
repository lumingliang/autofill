#!/usr/bin/env python3
"""
重置用户密码脚本
用法:
    python scripts/reset_passwords.py              # 重置所有用户密码为 123456
    python scripts/reset_passwords.py admin        # 重置指定用户密码为 123456
    python scripts/reset_passwords.py admin 888888 # 重置指定用户密码为指定密码
"""

import sys
import asyncio
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.password import get_password_hash
from app.models.admin import User


async def reset_all_passwords(new_password: str = "123456"):
    """重置所有用户密码"""
    from tortoise import Tortoise
    from app.settings.config import settings

    # 初始化数据库连接
    await Tortoise.init(config=settings.TORTOISE_ORM)

    # 生成新密码哈希
    hashed_password = get_password_hash(new_password)

    # 获取所有用户
    users = await User.all()

    print(f"找到 {len(users)} 个用户")
    print(f"正在将所有用户密码重置为: {new_password}")

    for user in users:
        old_password = user.password
        user.password = hashed_password
        await user.save()
        print(f"  ✓ 用户 '{user.username}' (ID: {user.id}) 密码已重置")
        print(f"    旧密码哈希: {old_password[:30]}...")
        print(f"    新密码哈希: {hashed_password[:30]}...")

    print(f"\n✅ 成功重置 {len(users)} 个用户的密码")

    # 关闭数据库连接
    await Tortoise.close_connections()


async def reset_user_password(username: str, new_password: str = "123456"):
    """重置指定用户密码"""
    from tortoise import Tortoise
    from app.settings.config import settings

    # 初始化数据库连接
    await Tortoise.init(config=settings.TORTOISE_ORM)

    # 查找用户
    user = await User.filter(username=username).first()

    if not user:
        print(f"❌ 用户 '{username}' 不存在")
        await Tortoise.close_connections()
        return

    # 生成新密码哈希
    hashed_password = get_password_hash(new_password)

    old_password = user.password
    user.password = hashed_password
    await user.save()

    print(f"✅ 用户 '{username}' (ID: {user.id}) 密码已重置为: {new_password}")
    print(f"   旧密码哈希: {old_password[:30]}...")
    print(f"   新密码哈希: {hashed_password[:30]}...")

    # 关闭数据库连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 重置所有用户密码为 123456
        asyncio.run(reset_all_passwords())
    elif len(sys.argv) == 2:
        # 重置指定用户密码为 123456
        username = sys.argv[1]
        asyncio.run(reset_user_password(username))
    elif len(sys.argv) >= 3:
        # 重置指定用户密码为指定密码
        username = sys.argv[1]
        new_password = sys.argv[2]
        asyncio.run(reset_user_password(username, new_password))
    else:
        print(__doc__)
        sys.exit(1)
