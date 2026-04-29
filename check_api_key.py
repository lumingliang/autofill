#!/usr/bin/env python3
"""
检查 API Key 对应的租户信息
"""

import asyncio
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

from app.models.autofill import AppManagement
from app.models.admin import Tenant


async def check_api_key():
    """检查 API Key"""
    api_key = "af_1fzDujUFl7SLg9L3CWMSV5upBT4GU1bR"

    app = await AppManagement.filter(api_key=api_key, is_active=True).first()
    if app:
        print(f"✅ 找到应用:")
        print(f"   - App Name: {app.app_name}")
        print(f"   - Tenant ID: {app.tenant_id}")

        tenant = await Tenant.filter(id=app.tenant_id).first()
        if tenant:
            print(f"   - Tenant Name: {tenant.name}")
            print(f"   - Tenant Domain: {tenant.domain}")
        else:
            print(f"   - 未找到租户信息")
    else:
        print(f"❌ 未找到 API Key 对应的应用")


if __name__ == "__main__":
    asyncio.run(check_api_key())
