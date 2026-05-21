"""
测试填单服务层 - 新实现：直接关联应用，不再关联页面
封装参数并通过 HTTP 请求调用 step_llm_fill_handler 接口
"""
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi.exceptions import HTTPException

from app.log import logger
from app.models.autofill import AppManagement, FieldGroupConfig, FieldSpec
from app.services.llm.llm_config_service import llm_config_service


class TestFillService:
    """测试填单服务"""

    @staticmethod
    async def chat_session(
        tenant_id: int,
        app_name: str,
        session_id: Optional[str],
        system_prompt: Optional[str],
        message: str,
        clear_history: bool = False
    ) -> Dict[str, Any]:
        """
        聊天会话处理 - 支持多轮对话（保持原有逻辑）
        """
        from app.services.llm.llm_proxy_service import llm_proxy_service
        from datetime import datetime

        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        # 使用默认系统提示词
        if not system_prompt:
            system_prompt = """你是一个专业的客服对话生成专家。请根据用户的要求生成真实的客服与用户的对话记录。

生成要求：
1. 对话格式：每轮对话包含"客服："和"用户："两部分
2. 对话内容要真实自然，符合实际客服场景
3. 用户问题要具体、有细节
4. 客服回复要专业、有帮助
5. 对话要有逻辑连贯性，前后呼应
6. 严格按照用户要求的轮数生成

输出格式示例：
客服：您好，欢迎咨询，请问有什么可以帮您？
用户：你好，我的车出了点问题。
客服：请问是什么车型？具体什么问题？
用户：比亚迪汉EV，突然无法启动了。
...

请根据用户的要求生成对话记录。"""

        # 生成新的session_id
        if not session_id or clear_history:
            session_id = f"chat_{uuid.uuid4().hex[:16]}"

        # 获取LLM配置
        config = await llm_config_service.get_default_config()

        if not config:
            raise HTTPException(status_code=500, detail="No LLM configuration found")

        try:
            start_time = time.time()

            result = await llm_proxy_service.process_request(
                query=message,
                system_prompt=system_prompt,
                config=config,
                method="plain"
            )

            elapsed_time = time.time() - start_time

            # plain 模式返回的数据结构
            # result 结构: {"success": ..., "data": {"raw_response": ..., "content": ...}, ...}
            data = result.get("data", {})
            assistant_content = data.get("raw_response", "")
            if not assistant_content:
                assistant_content = data.get("content", "") or data.get("response", "") or str(result)

            # 构建历史记录
            history = [
                {"role": "user", "content": message, "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": assistant_content, "timestamp": datetime.now().isoformat()}
            ]

            return {
                "session_id": session_id,
                "message": assistant_content,
                "history": history,
                "model": config.litellm_params.get("model", "unknown"),
                "usage": {
                    "prompt_tokens": result.get("_meta", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("_meta", {}).get("completion_tokens", 0)
                },
                "elapsed_time": elapsed_time
            }

        except Exception as e:
            logger.error(f"Chat session failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

    @staticmethod
    async def test_fill(
        tenant_id: int,
        app_name: str,
        group_names: List[str],
        field_names: List[str],
        chat_record: str
    ) -> Dict[str, Any]:
        """
        测试填单功能
        根据应用名称、字段组名称列表、字段名称列表和聊天记录进行填单
        1. 根据app_name+tenant_id查询api_key
        2. 构造参数，通过HTTP请求调用 step_llm_fill_handler 接口
        """
        if not app_name:
            raise HTTPException(status_code=400, detail="app_name is required")
        if not group_names:
            raise HTTPException(status_code=400, detail="group_names is required")
        if not chat_record:
            raise HTTPException(status_code=400, detail="chat_record is required")

        # 1. 查询应用信息
        app = await AppManagement.filter(
            app_name=app_name,
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if not app:
            raise HTTPException(status_code=404, detail=f"App with name '{app_name}' not found")

        # 2. 查询字段组信息
        groups = await FieldGroupConfig.filter(
            app_name=app_name,
            tenant_id=tenant_id,
            group_name__in=group_names,
            is_active=True
        ).all()
        if not groups:
            raise HTTPException(status_code=404, detail=f"Field groups not found: {group_names}")

        # 3. 如果指定了字段名，查询字段信息
        if field_names:
            fields = await FieldSpec.filter(
                app_name=app_name,
                tenant_id=tenant_id,
                field_name__in=field_names,
                is_active=True
            ).all()
            if not fields:
                raise HTTPException(status_code=404, detail="Fields not found")
            valid_field_names = [f.field_name for f in fields]
        else:
            valid_field_names = []

        # 4. 生成session_id
        session_id = f"test_{uuid.uuid4().hex[:12]}"

        # 5. 构造请求参数（符合新接口格式）
        request_data = {
            "session_id": session_id,
            "field_names": valid_field_names,
            "group_names": group_names,
            "system_prompt_group": group_names[0] if group_names else None,
            "query": chat_record,
            "method": None,
            "system_prompt": None,
            "include_reason": False,
            "memory_rounds": 0,
            "additional_data": None,
            "use_additional_data": False,
            "is_last": True
        }

        # 6. 调用 step_llm_fill_handler 接口
        # 使用内部HTTP请求访问public接口
        try:
            # 从环境变量获取端口，默认为 9999（与 run.py 一致）
            port = int(os.environ.get('APP_PORT', '9999'))
            base_url = f"http://localhost:{port}"
            url = f"{base_url}/api/autofill/llm/fill/step"

            # 构建请求头，使用API Key认证
            headers = {
                "Authorization": f"Bearer {app.api_key}",
                "Content-Type": "application/json"
            }

            start_time = time.time()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=request_data,
                    headers=headers,
                    timeout=120.0
                )

            elapsed_time = time.time() - start_time

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"step_llm_fill_handler error: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"填单处理失败: {error_detail}"
                )

            result = response.json()

            # 添加额外信息到结果
            if result.get("code") == 200:
                data = result.get("data", {})
                data["elapsed_time"] = elapsed_time
                data["app_name"] = app_name
                return data
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("msg", "填单处理失败")
                )

        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise HTTPException(status_code=500, detail=f"请求填单服务失败: {str(e)}")
        except Exception as e:
            logger.error(f"Test fill error: {e}")
            raise HTTPException(status_code=500, detail=f"填单测试失败: {str(e)}")


# 创建服务实例
test_fill_service = TestFillService()
