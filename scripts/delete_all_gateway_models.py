#!/usr/bin/env python3
"""
删除 LiteLLM 网关中的所有模型

用法:
    python scripts/delete_all_gateway_models.py

环境变量:
    LITELLM_BASE_URL - LiteLLM 网关地址 (默认: http://localhost:4000)
    LITELLM_MASTER_KEY - LiteLLM Master Key
"""
import asyncio
import os
import sys

import httpx

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.log import logger
from app.settings.config import settings


def get_litellm_config():
    """获取 LiteLLM 配置"""
    litellm_config = settings.LITELLM_CONFIG
    base_url = litellm_config.get("base_url", "http://localhost:4000").rstrip("/")
    master_key = litellm_config.get("master_key", "")
    return base_url, master_key


def get_headers(master_key: str) -> dict:
    """获取请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {master_key}"
    }


async def get_all_models(base_url: str, master_key: str) -> list:
    """获取网关中的所有模型"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/model/info",
                headers=get_headers(master_key),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return []


async def delete_model(base_url: str, master_key: str, model_id: str, model_name: str) -> bool:
    """删除单个模型"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/model/delete",
                headers=get_headers(master_key),
                json={"id": model_id},
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"已删除模型: {model_name} (ID: {model_id})")
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.info(f"模型不存在（已删除）: {model_name}")
            return True
        # 400 错误可能是配置文件中的模型，无法通过 API 删除
        if e.response.status_code == 400:
            error_text = e.response.text
            if "not found in db" in error_text:
                logger.warning(f"模型不在数据库中（可能是配置文件加载）: {model_name} (ID: {model_id})")
                # 视为成功，因为这不是我们能删除的
                return True
        logger.error(f"删除模型失败 {model_name}: HTTP {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"删除模型失败 {model_name}: {e}")
        return False


async def main():
    """主函数"""
    base_url, master_key = get_litellm_config()

    print(f"LiteLLM 网关地址: {base_url}")
    print(f"Master Key: {'*' * 10 if master_key else '未设置'}")
    print()

    if not master_key:
        print("错误: 未设置 LITELLM_MASTER_KEY")
        sys.exit(1)

    # 获取所有模型
    print("正在获取网关中的模型列表...")
    models = await get_all_models(base_url, master_key)
    print(f"找到 {len(models)} 个模型")
    print()

    if not models:
        print("网关中没有模型，无需删除")
        return

    # 显示将要删除的模型
    print("将要删除以下模型:")
    for model in models:
        model_name = model.get("model_name", "unknown")
        model_id = model.get("model_info", {}).get("id", "N/A")
        print(f"  - {model_name} (ID: {model_id})")
    print()

    # 确认删除
    confirm = input("确认删除所有模型? [y/N]: ")
    if confirm.lower() != "y":
        print("已取消")
        return

    print()
    print("开始删除...")

    # 删除所有模型
    success_count = 0
    fail_count = 0
    skipped_count = 0

    for model in models:
        model_name = model.get("model_name", "")
        model_id = model.get("model_info", {}).get("id", "")
        if not model_name or not model_id:
            continue

        result = await delete_model(base_url, master_key, model_id, model_name)
        if result:
            success_count += 1
        else:
            fail_count += 1

    print()
    print(f"删除完成: 成功 {success_count}, 失败 {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
