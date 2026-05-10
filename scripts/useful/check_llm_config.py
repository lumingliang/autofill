#!/usr/bin/env python3
"""
检查当前 LLM 配置
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 设置环境变量
os.environ.setdefault("APP_ENV", "dev")

from app.core.init_app import init_db
from app.models.llm_config import LLMConfig

async def main():
    await init_db()

    configs = await LLMConfig.filter(is_active=True).all()

    print("=" * 80)
    print("当前活跃的 LLM 配置")
    print("=" * 80)

    for config in configs:
        print(f"\n配置ID: {config.id}")
        print(f"  名称: {config.name}")
        print(f"  提供商: {config.model_provider}")
        print(f"  是否默认: {config.is_default}")
        print(f"  租户ID: {config.tenant_id}")
        print(f"  应用名: {config.app_name}")
        print(f"  LiteLLM参数:")
        litellm_params = config.litellm_params or {}
        for key, value in litellm_params.items():
            if key in ['api_key', 'master_key']:
                print(f"    {key}: ***")
            else:
                print(f"    {key}: {value}")

        print(f"  能力配置:")
        capabilities = config.capabilities or {}
        structured_methods = capabilities.get('structured_output_methods', {})
        for method, method_config in structured_methods.items():
            supported = method_config.get('supported', True)
            failed_count = method_config.get('failed_count', 0)
            status = "✓" if supported else "✗"
            print(f"    {status} {method}: supported={supported}, failed_count={failed_count}")

if __name__ == "__main__":
    asyncio.run(main())
