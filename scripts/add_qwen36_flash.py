#!/usr/bin/env python3
"""
基于现有模型配置复制并新增模型到 LLM 管理页面，同时同步到 LiteLLM 网关。

用法:
    python scripts/add_qwen36_flash.py [source_model_id] [target_model_id]

示例:
    python scripts/add_qwen36_flash.py qwen3.6-plus qwen3.6-flash
"""
import argparse
import os
import sys
import uuid
from pathlib import Path

import pymysql
import requests
import toml


def load_config(config_path: str = "config.toml") -> dict:
    """从项目根目录的 config.toml 读取配置"""
    if not os.path.exists(config_path):
        project_root = Path(__file__).resolve().parent.parent
        config_path = project_root / config_path
    return toml.load(config_path)


def load_db_config(config: dict) -> dict:
    """读取 MySQL 数据库配置"""
    mysql = config.get("database", {}).get("mysql", {})
    return {
        "host": mysql.get("host", "127.0.0.1"),
        "port": mysql.get("port", 3306),
        "user": mysql.get("user", "root"),
        "password": mysql.get("password", ""),
        "database": mysql.get("database", "autofill"),
    }


def load_litellm_config(config: dict) -> dict:
    """读取 LiteLLM 网关配置"""
    litellm = config.get("litellm", {})
    return {
        "base_url": litellm.get("base_url", "http://localhost:4000").rstrip("/"),
        "master_key": litellm.get("master_key", ""),
    }


def sync_to_litellm(config: dict, litellm_config: dict) -> tuple[bool, str]:
    """调用 LiteLLM /model/new API 注册模型"""
    provider = config.get("model_provider", "openai") or "openai"
    model_id = config["model_id"]
    litellm_model = f"{provider}/{model_id}"

    payload = {
        "model_name": model_id,
        "litellm_params": {
            "model": litellm_model,
            "timeout": config.get("timeout", 300),
            "api_key": config.get("api_key", ""),
            "api_base": config.get("api_base", ""),
        },
        "model_info": {
            "mode": "chat",
            "max_tokens": 4096,
            "supports_vision": False,
            "supports_function_calling": True,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {litellm_config['master_key']}",
    }

    url = f"{litellm_config['base_url']}/model/new"
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        gateway_model_id = result.get("model_id", "") or result.get("id", "")
        return True, gateway_model_id
    except requests.HTTPError as e:
        print(f"❌ LiteLLM 同步失败: HTTP {e.response.status_code} - {e.response.text}")
        return False, ""
    except Exception as e:
        print(f"❌ LiteLLM 同步失败: {e}")
        return False, ""


def main():
    parser = argparse.ArgumentParser(description="复制 LLM 模型配置并新增模型")
    parser.add_argument("source", nargs="?", default="qwen3.6-plus", help="源模型 Model ID")
    parser.add_argument("target", nargs="?", default="qwen3.6-flash", help="目标模型 Model ID")
    args = parser.parse_args()

    source_model_id = args.source
    target_model_id = args.target

    full_config = load_config()
    db_config = load_db_config(full_config)
    litellm_config = load_litellm_config(full_config)

    conn = pymysql.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cursor:
            # 查询源模型配置
            cursor.execute(
                "SELECT * FROM llm_config WHERE model_id = %s",
                (source_model_id,),
            )
            source = cursor.fetchone()

            if not source:
                print(f"❌ 未找到源模型配置: {source_model_id}")
                sys.exit(1)

            # 检查目标模型是否已存在
            cursor.execute(
                "SELECT id FROM llm_config WHERE model_id = %s",
                (target_model_id,),
            )
            existing = cursor.fetchone()
            if existing:
                print(f"⚠️ 目标模型已存在: {target_model_id}")
                sys.exit(0)

            # 同步到 LiteLLM 网关
            print(f"🔄 正在将 {target_model_id} 同步到 LiteLLM 网关...")
            success, gateway_model_id = sync_to_litellm(source, litellm_config)
            if not success:
                print("⚠️ 继续写入本地数据库，但网关同步失败")
                gateway_model_id = str(uuid.uuid4())
            else:
                print(f"✅ LiteLLM 网关注册成功: {gateway_model_id}")

            # 复制配置到本地数据库
            insert_sql = """
                INSERT INTO llm_config (
                    created_at, updated_at, model_id, model_provider, capabilities,
                    is_active, is_default, description, api_base, api_key, timeout,
                    gateway_model_id
                )
                SELECT
                    NOW(), NOW(), %s, model_provider, capabilities,
                    is_active, is_default, %s, api_base, api_key, timeout, %s
                FROM llm_config
                WHERE model_id = %s
            """
            description = f"复制自 {source_model_id}"
            cursor.execute(
                insert_sql,
                (target_model_id, description, gateway_model_id, source_model_id),
            )
            conn.commit()

            print(f"✅ 已新增模型: {target_model_id}")
            print(f"   源模型: {source_model_id}")
            print(f"   gateway_model_id: {gateway_model_id}")
            print(f"   provider: {source['model_provider']}")
            print(f"   api_base: {source['api_base']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
